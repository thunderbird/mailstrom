#!/usr/bin/env python3
"""Correlate CalDAV probe failures against Stalwart's CloudWatch logs.

Reads the JSONL emitted by probe.py, finds every non-OK attempt, and for each one
queries the Stalwart CloudWatch log group in a window around the failure timestamp,
filtered to this machine's public IP. The report tells you, for each probe failure,
exactly what the server logged at that moment -- or that it logged nothing at all.

    probe fails + server logged an error   -> server-side (Stalwart)
    probe fails (TCP/TLS/timeout) + silent  -> network / edge / load balancer
    probe never fails but users still do    -> client-side (Thunderbird desktop)

Requires the AWS CLI, authenticated to the legacy profile:

    AWS_PROFILE=mzla-legacy python3 correlate.py probe-YYYYMMDD.jsonl

Options:
    --log-group   CloudWatch log group   (default: /tb/prod/stalwart)
    --window      seconds each side of the failure to search (default: 90)
    --profile     AWS profile to pass to the CLI (default: $AWS_PROFILE or mzla-legacy)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_ts(ts: str) -> int:
    """ISO 'YYYY-MM-DDTHH:MM:SSZ' -> epoch milliseconds."""
    dt = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def query_logs(log_group: str, start_ms: int, end_ms: int, ip: str | None,
               profile: str) -> list[dict]:
    cmd = [
        'aws', 'logs', 'filter-log-events',
        '--log-group-name', log_group,
        '--start-time', str(start_ms),
        '--end-time', str(end_ms),
        '--limit', '50',
        '--output', 'json',
        '--profile', profile,
    ]
    if ip:
        # Filter to events mentioning our probe's public IP so we only see the
        # server's view of *our* connections.
        cmd += ['--filter-pattern', f'"{ip}"']
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f'    ! aws query failed: {proc.stderr.strip()}', file=sys.stderr)
        return []
    return json.loads(proc.stdout or '{}').get('events', [])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('jsonl', nargs='+', help='probe-*.jsonl file(s) to analyze')
    ap.add_argument('--log-group', default='/tb/prod/stalwart')
    ap.add_argument('--window', type=int, default=90, help='seconds each side of failure')
    ap.add_argument('--profile', default=None)
    args = ap.parse_args()

    import os
    profile = args.profile or os.environ.get('AWS_PROFILE') or 'mzla-legacy'

    failures = []
    total = 0
    for path_str in args.jsonl:
        path = Path(path_str)
        if not path.exists():
            print(f'skipping missing file: {path}', file=sys.stderr)
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            total += 1
            if rec.get('outcome') != 'OK':
                failures.append(rec)

    print(f'Analyzed {total} probe attempts, {len(failures)} failures.\n')
    if not failures:
        print('No probe failures recorded -- if users still report errors, the '
              'issue is likely client-side (Thunderbird desktop) or in a layer this '
              'probe does not exercise.')
        return 0

    window_ms = args.window * 1000
    server_confirmed = 0
    server_silent = 0

    for rec in failures:
        ts = rec['ts']
        ip = rec.get('public_ip')
        print('=' * 78)
        print(f'FAILURE {ts}  outcome={rec["outcome"]}  status={rec.get("http_status")}')
        print(f'  error : {rec.get("error")}')
        print(f'  phases: {rec.get("phases")}  total={rec.get("total_ms")}ms  probe_ip={ip}')
        center = parse_ts(ts)
        events = query_logs(args.log_group, center - window_ms, center + window_ms, ip, profile)
        if not events:
            server_silent += 1
            print(f'  SERVER SILENT: no {args.log_group} events for {ip} in '
                  f'+/-{args.window}s window  --> points AWAY from Stalwart '
                  f'(network / edge / client).')
        else:
            server_confirmed += 1
            print(f'  SERVER LOGGED {len(events)} event(s) in window:')
            for ev in events:
                ev_ts = datetime.fromtimestamp(ev['timestamp'] / 1000, timezone.utc)
                print(f'    {ev_ts:%H:%M:%SZ}  {ev["message"].strip()[:220]}')
        print()

    print('=' * 78)
    print(f'SUMMARY: {len(failures)} failures | server-logged: {server_confirmed} | '
          f'server-silent: {server_silent}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
