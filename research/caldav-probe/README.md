# CalDAV intermittent-connection probe

Diagnostic tooling for the intermittent *"failed to connect to server
mail.thundermail.com"* calendar errors that Thunderbird desktop users
occasionally see. A once-a-day integration test can't catch a failure that
happens roughly once every 2–3 hours, so this polls the CalDAV endpoint
frequently and records exactly which connection phase fails, then correlates any
failures against Stalwart's CloudWatch logs.

The point is to answer one question: **is the root cause Stalwart, the
network/edge, or the Thunderbird client?** The root cause may well be unrelated
to Stalwart — this is how we find out for sure.

## Contents

- `probe.py` — polls `https://<host>/dav/cal/` on an interval, timing each phase
  (DNS → TCP → TLS → CalDAV `PROPFIND`) and classifying failures
  (`DNS_FAIL`, `TCP_FAIL`, `TLS_FAIL`, `AUTH_FAIL`, `HTTP_5XX`, `TIMEOUT`,
  `DAV_ERROR`, `OK`). Standard library only — no install step. Appends one JSON
  line per attempt to `probe-YYYYMMDD.jsonl`.
- `correlate.py` — reads the JSONL, finds failures, and queries the Stalwart
  CloudWatch log group in a window around each failure, filtered to this
  machine's public IP.

## Usage

```bash
cd research/caldav-probe
cp .env.example .env      # then fill in TEST_ACCT_1 credentials

# Run the probe (leave it going for several hours / overnight):
python3 probe.py

# Later, correlate failures against Stalwart logs (needs AWS SSO to legacy):
AWS_PROFILE=mzla-legacy python3 correlate.py probe-*.jsonl
```

## Reading the results

| Probe result | Stalwart logs | Verdict |
|---|---|---|
| Fails | error logged at our IP/time | **Server-side (Stalwart)** |
| `TLS_FAIL` (cert) | — | Cert / edge |
| `TCP_FAIL` / `TIMEOUT` | silent | **Network / edge / load balancer** |
| Always `OK` | — | **Client-side (Thunderbird)** or a layer not probed |

`.env` and the `*.jsonl` capture files are gitignored.
