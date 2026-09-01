# Operations Guide

Production operations guide for the fusion-code-modelization REST API server.

## Deployment

### Prerequisites

- Python 3.12+ (shared monorepo `.venv` at `/Users/dahai/fusion/.venv`)
- `fusion-core` installed (`pip install -e fusion-core`)
- `fusion-code-modelization` installed (`pip install -e ".[test]"`)
- **fusion-gateway** running on `localhost:11432/v1` (inference upstream)
  - gateway upstream: fusion-mlx on `localhost:11434` (`~/claude-home/fusion-mlx/start.sh start`)
  - a model loaded by the gateway matching `DEFAULT_LOCAL_MODEL` (`Qwen3.5-9B-4bit`)

### Start / Stop / Status

```bash
./start.sh start     # launch REST API (default 127.0.0.1:11459)
./start.sh stop      # graceful stop (SIGTERM, then SIGKILL after 10s)
./start.sh restart   # stop + start
./start.sh status    # PID + health probe, exit 0 if running
./start.sh log [-f]  # tail last 100 lines (or follow)
```

### Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `FUSION_FCM_HOST` | `127.0.0.1` | bind host (non-loopback requires `--allow-nonloopback`) |
| `FUSION_FCM_PORT` | `11459` | bind port |
| `FUSION_GATEWAY_URL` | `http://localhost:11432/v1` | inference gateway URL |
| `FUSION_MODEL_ID` | `Qwen3.5-9B-4bit` | model id (must match a gateway-loaded model) |
| `FUSION_TIMEOUT` | `120.0` | per-request LLM timeout (seconds) |
| `FUSION_RETRY_ATTEMPTS` | `2` | LLM retry count on transient failure |
| `FUSION_SERVER_API_KEY` | (none) | bearer token clients must present; falls back to `FUSION_MLX_API_KEY` then `MLX_API_KEY`; empty = auth disabled |
| `FUSION_LOG_LEVEL` | `INFO` | root log level |

> **Security:** bind loopback only by default. To expose on a LAN, pass `--allow-nonloopback` and **set `FUSION_SERVER_API_KEY`** — unauthenticated non-loopback exposure is rejected.

## Deployment runbook

Step-by-step release procedure. Editable install (`pip install -e`) means source = deployment — no build artifact, no artifact registry. Every release is a `git checkout` + deps sync + restart.

### Pre-flight (before every release)

```bash
cd /Users/dahai/fusion/fusion-code-modenization
git fetch origin && git log --oneline HEAD..origin/main    # confirm what's incoming
gh pr checks <PR>                                           # CI must be all green
```

- CI: all 5 jobs green (test 3.12/3.13, lint, typecheck, security).
- `bandit -r fusion_code_modelization/ -ll -ii` → 0 issues locally.
- Confirm the release commit is tagged or noted in `CHANGELOG.md`.

### Release: standard update

```bash
# 1. Activate shared venv
source /Users/dahai/fusion/.venv/bin/activate

# 2. Pull the release commit
git pull --ff-only origin main

# 3. Sync deps (fusion-core + this package + extras)
pip install -e fusion-core
pip install -e ".[test,server]"

# 4. Smoke test before restarting the live server
pytest tests/ -q                      # all green
python -c "from fusion_code_modelization.server.app import create_app; create_app()"

# 5. Restart the server
./start.sh restart
./start.sh status                     # exit 0 + health probe
curl -fsS http://127.0.0.1:11459/health | python -m json.tool   # status: ok

# 6. Confirm inference path end-to-end (needs gateway up + model loaded)
curl -fsS http://127.0.0.1:11432/v1/models | python -m json.tool # model present
```

### Rollback (release bad)

No DB, no migrations — rollback is a `git checkout` + restart:

```bash
git log --oneline -10                 # find last-known-good commit
git checkout <good-commit>
pip install -e ".[test,server]"       # re-sync if deps changed
./start.sh restart
./start.sh status
curl -fsS http://127.0.0.1:11459/health    # status: ok
```

If the bad commit changed `pyproject.toml` deps, `pip install` re-syncs to the rolled-back manifest. If it changed `fusion-core`, also `pip install -e fusion-core`.

### First-time production install

```bash
source /Users/dahai/fusion/.venv/bin/activate          # create via repo root scripts/sync-deps.sh
pip install -e fusion-core
pip install -e ".[server]"                             # server extras only for prod
# set secrets (see Secret management & rotation)
export FUSION_SERVER_API_KEY="<key>"                   # registered in gateway config.yaml
./start.sh start
./start.sh status
```

### Health-check gate (all releases)

A release is **not complete** until all three pass:

1. `./start.sh status` → exit 0 (process alive).
2. `GET /health` → `{"status":"ok", "gateway":"ok", "disk":"ok"}`.
3. `GET /metrics` → counters respond (request rate non-zero if traffic flowing, or zero cleanly if idle).

If any fails, rollback immediately.

## Monitoring

### Health (`GET /health`, public)

Deep probe. Returns 200 `{"status":"ok",...}` when healthy, 503 `{"status":"degraded",...}` when a dependency is down. Checks:

- `gateway` — HTTP GET to `{gateway_url}/models`; `ok` / `HTTP <code>` / `unreachable: <Exception>`
- `disk` — free disk on home volume; `ok` if ≥1 GB free, `low` otherwise
- `disk_free_gb` — numeric free GB

Use this for liveness/readiness probes. A `degraded` status means the server is up but cannot serve inference — route traffic elsewhere or fix the upstream.

### Metrics (`GET /metrics`, public)

In-process counters (reset on restart):

```json
{
  "chat_total": 0,
  "chat_failed": 0,
  "chat_avg_latency_ms": 0.0,
  "workflow_total": 0,
  "workflow_failed": 0
}
```

Scrape periodically for error-rate and latency tracking. No Prometheus export — poll this JSON endpoint.

### Monitoring dashboard

The `/metrics` endpoint exposes JSON counters; there is no built-in UI. Build a dashboard in your existing observability stack (Grafana/Datadog/k9s) by polling `/metrics` at a fixed interval and graphing these series:

| Panel | Query (from `/metrics` JSON) | Alert threshold |
|---|---|---|
| Request rate | `chat_total` delta / scrape interval | — |
| Error rate | `chat_failed` delta / `chat_total` delta | >5% sustained 5 min |
| Avg latency | `chat_avg_latency_ms` (gauge) | p95 > 5000 ms |
| Workflow rate | `workflow_total` delta | — |
| Workflow failures | `workflow_failed` delta | >0 sustained 2 min |
| Health | `GET /health` → `status` field | `degraded` for >1 min |
| Gateway reachability | `GET /health` → `gateway` field | != `ok` for >1 min |
| Disk free | `GET /health` → `disk_free_gb` | <1 GB |

**Scrape config** (cron or sidecar, every 15s):

```bash
#!/bin/bash
# /usr/local/bin/fcm-scrape.sh — poll metrics, ship to your sink
URL="${FCM_URL:-http://127.0.0.1:11459}"
curl -fsS "$URL/metrics" | your_sink --source fcm
curl -fsS "$URL/health" | your_sink --source fcm --measurement health
```

**Alerting rules** (translate to your stack):

1. `health.status == "degraded"` for >1 min → page on-call (gateway or disk down; server cannot serve inference).
2. `chat_failed / chat_total > 0.05` over 5 min → page (model returning errors or empty content).
3. `chat_avg_latency_ms > 5000` over 5 min → warn (model overloaded or gateway slow).
4. `health.disk_free_gb < 1` → warn (free disk before snapshot/workflow persistence fails).

No persistent storage in-process — counters reset on restart. Persist deltas externally; treat restart as a counter reset (gap in rate panels, not a spike).

## Secret management & rotation

This server authenticates clients with a single bearer token (`FUSION_SERVER_API_KEY`, falling back to `FUSION_MLX_API_KEY` then `MLX_API_KEY`). The token must also be registered in **fusion-gateway** `config.yaml` `auth.api_keys` (the gateway uses it to authorize the upstream inference call). One secret, two places that must agree.

### Rotation procedure

Rotate on a schedule (every 90 days), after team turnover, or on suspected leak. Zero-downtime rotation uses the gateway's multi-key list — add the new key before removing the old.

1. **Generate** a new key:

   ```bash
   NEW_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
   echo "$NEW_KEY"
   ```

2. **Add** the new key to fusion-gateway (keep the old one present during cutover):

   ```yaml
   # fusion-gateway config.yaml — auth.api_keys
   auth:
     enabled: true
     api_keys:
       - key: "<OLD_KEY>"      # keep during cutover
         allowed_models: ["*"]
       - key: "<NEW_KEY>"      # add
         allowed_models: ["*"]
   ```

   Reload the gateway per its docs (restart or SIGHUP).

3. **Roll clients** to the new key: update each client's `FUSION_SERVER_API_KEY` (or `Authorization: Bearer` header) and restart them. Old key still works, so no client downtime.

4. **Switch the server** to the new key:

   ```bash
   export FUSION_SERVER_API_KEY="$NEW_KEY"
   ./start.sh restart
   ./start.sh status          # confirm health: ok
   ```

5. **Verify** no client still uses the old key — check server logs for `auth rejected` from lingering clients, or query clients. Confirm via `/metrics` that request rate is steady.

6. **Remove** the old key from the gateway `auth.api_keys`, reload. Old key now rejected.

### Storage

- **Never** commit keys to the repo. Load from environment (systemd `EnvironmentFile=`, launchd `EnvironmentVariables`, or a secrets manager).
- **systemd unit** example:

  ```ini
  [Service]
  EnvironmentFile=/etc/fusion/fcm.env   # chmod 600, owner root
  ExecStart=/Users/dahai/fusion/.venv/bin/fusion-code-modelization serve
  ```

  `/etc/fusion/fcm.env`:

  ```sh
  FUSION_SERVER_API_KEY=<key>
  FUSION_GATEWAY_URL=http://localhost:11432/v1
  ```

- **Compromise response**: if a key leaks, skip to step 6 (remove from gateway immediately), generate a fresh key, and rotate — old key is dead before clients update, so expect a brief auth-failure window.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `/health` → 503 `gateway: unreachable` | fusion-gateway down or wrong `FUSION_GATEWAY_URL` | `curl {gateway_url}/models`; start gateway |
| `/health` → 503 `gateway: HTTP 404` | gateway up but `/models` route missing | check gateway version/config |
| `/health` → 503 `disk: low` | <1 GB free on home volume | free disk |
| chat → 401 `invalid or missing bearer token` | `FUSION_SERVER_API_KEY` set, client lacked/mismatched token | send `Authorization: Bearer <key>` |
| chat → 400 `empty_content` | LLM returned blank response (issue #14 guard) | retry; if persistent, check model load |
| chat → 429 `rate limit exceeded` | >60 req/min from one client IP | reduce rate or raise `rate_limit` in `create_app()` |
| `start.sh start` → "process exited early" | import error or port in use | `./start.sh log`; check `STDERR_LOG` |

### Logs

- `logs/stdout.log` — request/access logs
- `logs/stderr.log` — errors + tracebacks

## State Persistence

Workflow results are persisted to `~/.fusion/code_mod/workflow_results.json` via the FastAPI lifespan:

- **startup** — restores prior workflow results into memory (logged count); corrupt file → warning, fresh start
- **shutdown** — writes current results atomically; OS error → logged, results lost

Session/snapshot state lives under the `SessionStore` base dir (temp dir in tests, default `~/.fusion/...` in production).

## Rollback

See **Rollback (release bad)** under [Deployment runbook](#deployment-runbook) — editable install means rollback is a `git checkout` + restart, no DB or migrations.

## Upstream Gaps

Issues requiring upstream fixes (file issues at the respective repo, then PR):

1. **fusion-gateway `/models` route** — required for the `/health` deep probe. If a gateway version omits it, `/health` always reports `degraded`. Verify gateway exposes `GET /v1/models` returning 200.
2. **fusion-gateway auth key registration** — `FUSION_SERVER_API_KEY` must be registered in the gateway's `config.yaml` `auth.api_keys`; it is **not** the fusion-mlx key. Mismatch → gateway 401 on inference.
3. **fusion-mlx model id** — `DEFAULT_LOCAL_MODEL` (`Qwen3.5-9B-4bit`) must match a model the gateway's fusion-mlx upstream has loaded. Mismatch → inference failures. Verify via `~/claude-home/fusion-mlx/start.sh status`.

When an upstream gap blocks this package, follow the monorepo flow: open an issue on the upstream project first, then a PR — do not patch upstream code from this repo.
