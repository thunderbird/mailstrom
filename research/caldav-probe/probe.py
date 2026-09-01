#!/usr/bin/env python3
"""Intermittent CalDAV connection probe.

Polls the Thundermail CalDAV endpoint on a fixed interval and records, for every
attempt, a per-phase breakdown (DNS -> TCP -> TLS -> CalDAV request) with precise
failure classification. The goal is to catch the *intermittent* "failed to connect
to server" errors that Thunderbird desktop users see for the calendar, and to
pin down which layer fails so we can tell whether the root cause is Stalwart, the
network/edge, or the client.

Deliberately uses only the Python standard library so it runs anywhere with no
install step, and so each connection phase can be timed and classified on its own
(the `caldav` library collapses every failure into a single opaque exception).

Each attempt is appended as one JSON line to probe-YYYYMMDD.jsonl. Feed that file
to correlate.py to line failures up against Stalwart's CloudWatch logs.

Config comes from the environment (optionally from a .env file next to this
script):

    TEST_SERVER_HOST        host to probe          (default: mail.thundermail.com)
    TEST_ACCT_1_USERNAME    CalDAV username        (required)
    TEST_ACCT_1_PASSWORD    CalDAV app password    (required)
    CALDAV_PATH             PROPFIND path          (default: /dav/cal/)
    PROBE_INTERVAL_SECONDS  seconds between polls   (default: 60)
    PROBE_TIMEOUT_SECONDS   per-phase timeout       (default: 30)
"""

from __future__ import annotations

import base64
import json
import os
import signal
import socket
import ssl
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Outcome classifications, ordered from earliest to latest failing phase.
OK = 'OK'
DNS_FAIL = 'DNS_FAIL'
TCP_FAIL = 'TCP_FAIL'
TLS_FAIL = 'TLS_FAIL'
AUTH_FAIL = 'AUTH_FAIL'
HTTP_5XX = 'HTTP_5XX'
DAV_ERROR = 'DAV_ERROR'
TIMEOUT = 'TIMEOUT'

PROPFIND_BODY = (
    '<?xml version="1.0" encoding="utf-8" ?>'
    '<d:propfind xmlns:d="DAV:"><d:prop><d:current-user-principal/></d:prop></d:propfind>'
).encode('utf-8')


def load_dotenv(path: Path) -> None:
    """Minimal .env loader (no dependency on python-dotenv)."""
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Don't clobber a value already exported in the real environment.
        os.environ.setdefault(key, value)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def get_public_ip() -> str | None:
    """Best-effort discovery of this machine's public IP for log correlation."""
    for url in ('https://checkip.amazonaws.com', 'https://api.ipify.org'):
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                return resp.read().decode('utf-8').strip()
        except Exception:
            continue
    return None


def probe_once(host: str, path: str, auth_header: str, timeout: float) -> dict:
    """Run one full DNS -> TCP -> TLS -> PROPFIND attempt, timing each phase."""
    result = {
        'ts': now_iso(),
        'outcome': None,
        'http_status': None,
        'phases': {},
        'total_ms': None,
        'error': None,
    }
    started = time.monotonic()

    def elapsed_ms(since: float) -> float:
        return round((time.monotonic() - since) * 1000, 1)

    # Phase 1: DNS
    t = time.monotonic()
    try:
        addrinfo = socket.getaddrinfo(host, 443, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as e:
        result.update(outcome=DNS_FAIL, error=f'{type(e).__name__}: {e}')
        result['total_ms'] = elapsed_ms(started)
        return result
    result['phases']['dns_ms'] = elapsed_ms(t)
    family, socktype, proto, _canon, sockaddr = addrinfo[0]
    result['resolved_ip'] = sockaddr[0]

    # Phase 2: TCP connect
    t = time.monotonic()
    raw_sock = socket.socket(family, socktype, proto)
    raw_sock.settimeout(timeout)
    try:
        raw_sock.connect(sockaddr)
    except socket.timeout as e:
        raw_sock.close()
        result.update(outcome=TIMEOUT, error=f'tcp connect timeout: {e}')
        result['total_ms'] = elapsed_ms(started)
        return result
    except OSError as e:
        raw_sock.close()
        result.update(outcome=TCP_FAIL, error=f'{type(e).__name__}: {e}')
        result['total_ms'] = elapsed_ms(started)
        return result
    result['phases']['tcp_ms'] = elapsed_ms(t)

    # Phase 3: TLS handshake (cert verification on)
    t = time.monotonic()
    ctx = ssl.create_default_context()
    try:
        tls_sock = ctx.wrap_socket(raw_sock, server_hostname=host)
    except ssl.SSLCertVerificationError as e:
        raw_sock.close()
        result.update(outcome=TLS_FAIL, error=f'cert verification: {e}')
        result['total_ms'] = elapsed_ms(started)
        return result
    except ssl.SSLError as e:
        raw_sock.close()
        result.update(outcome=TLS_FAIL, error=f'{type(e).__name__}: {e}')
        result['total_ms'] = elapsed_ms(started)
        return result
    except (socket.timeout, OSError) as e:
        raw_sock.close()
        result.update(outcome=TLS_FAIL, error=f'{type(e).__name__}: {e}')
        result['total_ms'] = elapsed_ms(started)
        return result
    result['phases']['tls_ms'] = elapsed_ms(t)

    # Phase 4: CalDAV PROPFIND
    t = time.monotonic()
    request = (
        f'PROPFIND {path} HTTP/1.1\r\n'
        f'Host: {host}\r\n'
        f'Authorization: {auth_header}\r\n'
        f'Depth: 0\r\n'
        f'Content-Type: application/xml; charset=utf-8\r\n'
        f'Content-Length: {len(PROPFIND_BODY)}\r\n'
        f'User-Agent: mailstrom-caldav-probe/1.0\r\n'
        f'Connection: close\r\n'
        f'\r\n'
    ).encode('utf-8') + PROPFIND_BODY
    try:
        tls_sock.settimeout(timeout)
        tls_sock.sendall(request)
        # Read just enough to get the status line.
        buf = b''
        while b'\r\n' not in buf and len(buf) < 4096:
            chunk = tls_sock.recv(4096)
            if not chunk:
                break
            buf += chunk
    except socket.timeout as e:
        tls_sock.close()
        result.update(outcome=TIMEOUT, error=f'propfind read timeout: {e}')
        result['total_ms'] = elapsed_ms(started)
        return result
    except OSError as e:
        tls_sock.close()
        result.update(outcome=DAV_ERROR, error=f'{type(e).__name__}: {e}')
        result['total_ms'] = elapsed_ms(started)
        return result
    finally:
        try:
            tls_sock.close()
        except OSError:
            pass
    result['phases']['req_ms'] = elapsed_ms(t)

    status_line = buf.split(b'\r\n', 1)[0].decode('latin-1', 'replace')
    parts = status_line.split(' ', 2)
    status = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
    result['http_status'] = status
    result['total_ms'] = elapsed_ms(started)

    if status in (200, 207):
        result['outcome'] = OK
    elif status in (401, 403):
        result.update(outcome=AUTH_FAIL, error=status_line)
    elif status is not None and 500 <= status < 600:
        result.update(outcome=HTTP_5XX, error=status_line)
    else:
        result.update(outcome=DAV_ERROR, error=status_line)
    return result


_stop = False


def _handle_signal(signum, _frame):
    global _stop
    _stop = True
    print(f'\n[{now_iso()}] received signal {signum}, shutting down after current attempt...',
          file=sys.stderr, flush=True)


def main() -> int:
    load_dotenv(HERE / '.env')

    host = os.environ.get('TEST_SERVER_HOST', 'mail.thundermail.com').strip()
    username = os.environ.get('TEST_ACCT_1_USERNAME', '').strip()
    password = os.environ.get('TEST_ACCT_1_PASSWORD', '').strip()
    path = os.environ.get('CALDAV_PATH', '/dav/cal/').strip()
    interval = float(os.environ.get('PROBE_INTERVAL_SECONDS', '60'))
    timeout = float(os.environ.get('PROBE_TIMEOUT_SECONDS', '30'))

    if not username or not password:
        print('ERROR: TEST_ACCT_1_USERNAME and TEST_ACCT_1_PASSWORD must be set '
              '(export them or put them in research/caldav-probe/.env).', file=sys.stderr)
        return 2

    auth_header = 'Basic ' + base64.b64encode(f'{username}:{password}'.encode()).decode()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    public_ip = get_public_ip()
    out_path = HERE / f'probe-{datetime.now(timezone.utc):%Y%m%d}.jsonl'

    print(f'[{now_iso()}] probing https://{host}{path} as {username} '
          f'every {interval:g}s (timeout {timeout:g}s)')
    print(f'[{now_iso()}] this machine public IP: {public_ip or "unknown"} '
          f'(use this to filter Stalwart logs)')
    print(f'[{now_iso()}] writing results to {out_path}')

    counts: dict[str, int] = {}
    attempts = 0
    while not _stop:
        cycle_start = time.monotonic()
        record = probe_once(host, path, auth_header, timeout)
        record['public_ip'] = public_ip
        record['host'] = host

        with out_path.open('a') as f:
            f.write(json.dumps(record) + '\n')

        attempts += 1
        counts[record['outcome']] = counts.get(record['outcome'], 0) + 1
        summary = ' '.join(f'{k}={v}' for k, v in sorted(counts.items()))
        flag = '' if record['outcome'] == OK else '  <-- FAILURE'
        print(f'[{record["ts"]}] {record["outcome"]:<9} '
              f'status={record["http_status"]} total={record["total_ms"]}ms '
              f'phases={record["phases"]}{flag}', flush=True)
        if record['outcome'] != OK and record['error']:
            print(f'            error: {record["error"]}', flush=True)
        if attempts % 10 == 0:
            print(f'[{now_iso()}] --- {attempts} attempts: {summary} ---', flush=True)

        # Sleep the remainder of the interval, interruptibly.
        while not _stop and (time.monotonic() - cycle_start) < interval:
            time.sleep(min(1.0, interval))

    print(f'[{now_iso()}] stopped after {attempts} attempts: '
          f'{" ".join(f"{k}={v}" for k, v in sorted(counts.items()))}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
