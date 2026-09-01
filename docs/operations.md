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

This package is installed editable (`pip install -e`) — source is the deployment. To roll back:

```bash
git log --oneline -10          # find last-known-good commit
git checkout <commit>          # editable install picks up source immediately
./start.sh restart
./start.sh status              # confirm health: ok
```

No schema migrations, no DB — rollback is a `git checkout` + restart.

## Upstream Gaps

Issues requiring upstream fixes (file issues at the respective repo, then PR):

1. **fusion-gateway `/models` route** — required for the `/health` deep probe. If a gateway version omits it, `/health` always reports `degraded`. Verify gateway exposes `GET /v1/models` returning 200.
2. **fusion-gateway auth key registration** — `FUSION_SERVER_API_KEY` must be registered in the gateway's `config.yaml` `auth.api_keys`; it is **not** the fusion-mlx key. Mismatch → gateway 401 on inference.
3. **fusion-mlx model id** — `DEFAULT_LOCAL_MODEL` (`Qwen3.5-9B-4bit`) must match a model the gateway's fusion-mlx upstream has loaded. Mismatch → inference failures. Verify via `~/claude-home/fusion-mlx/start.sh status`.

When an upstream gap blocks this package, follow the monorepo flow: open an issue on the upstream project first, then a PR — do not patch upstream code from this repo.
