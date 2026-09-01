#!/bin/bash
# fusion-code-modelization lifecycle manager (start|stop|restart|status|log)
# Owns the REST API server (default 127.0.0.1:11459, or $FUSION_FCM_PORT).
# Callers: fusion-studio UpstreamServiceManager, manual ops.
# Affected API: start.sh start|stop|restart|status|log; status exits 0 if running, 1 if not.
# Data schemas: PID file .fusion-code-modelization.pid; logs/stdout.log + logs/stderr.log.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PID_FILE="${SCRIPT_DIR}/.fusion-code-modelization.pid"
LOG_DIR="${SCRIPT_DIR}/logs"
STDOUT_LOG="${LOG_DIR}/stdout.log"
STDERR_LOG="${LOG_DIR}/stderr.log"
HEALTH_WAIT=30

HOST="${FUSION_FCM_HOST:-127.0.0.1}"
PORT="${FUSION_FCM_PORT:-11459}"
MLX_URL="${FUSION_GATEWAY_URL:-http://localhost:11432/v1}"

VENV="/Users/dahai/fusion/.venv"
PYTHON="${VENV}/bin/python"

log_info() { echo "[fcm $(date '+%H:%M:%S')] INFO: $*"; }
log_err()  { echo "[fcm $(date '+%H:%M:%S')] ERROR: $*" >&2; }

is_running() {
    [[ -f "$PID_FILE" ]] || return 1
    local pid
    pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
    [[ -n "$pid" ]] || return 1
    kill -0 "$pid" 2>/dev/null
}

cmd_start() {
    if is_running; then
        log_info "already running (pid $(cat "$PID_FILE"))"
        return 0
    fi
    mkdir -p "$LOG_DIR"
    log_info "starting on ${HOST}:${PORT} (mlx=${MLX_URL})"
    nohup "$PYTHON" -m fusion_code_modelization.server.runner \
        --host "$HOST" --port "$PORT" --mlx-url "$MLX_URL" \
        >"$STDOUT_LOG" 2>"$STDERR_LOG" &
    local pid=$!
    echo "$pid" > "$PID_FILE"
    log_info "started pid ${pid}, waiting for health..."
    local i=0
    while (( i < HEALTH_WAIT )); do
        if ! kill -0 "$pid" 2>/dev/null; then
            log_err "process exited early; see $STDERR_LOG"
            rm -f "$PID_FILE"
            return 1
        fi
        if curl -sf "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
            log_info "healthy (pid ${pid})"
            return 0
        fi
        sleep 1
        i=$(( i + 1 ))
    done
    log_err "health check timed out after ${HEALTH_WAIT}s; see $STDERR_LOG"
    return 1
}

cmd_stop() {
    if ! is_running; then
        log_info "not running"
        rm -f "$PID_FILE"
        return 0
    fi
    local pid
    pid=$(cat "$PID_FILE")
    log_info "stopping pid ${pid}"
    kill "$pid" 2>/dev/null || true
    local i=0
    while (( i < 10 )); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
        i=$(( i + 1 ))
    done
    if kill -0 "$pid" 2>/dev/null; then
        log_err "did not exit, sending SIGKILL"
        kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
    log_info "stopped"
}

cmd_status() {
    if is_running; then
        local pid
        pid=$(cat "$PID_FILE")
        log_info "running (pid ${pid})"
        if curl -sf "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
            log_info "health: ok"
        else
            log_err "health: unreachable"
        fi
        return 0
    fi
    log_info "not running"
    return 1
}

cmd_log() {
    local follow="${1:-}"
    if [[ "$follow" == "-f" || "$follow" == "--follow" ]]; then
        tail -f "$STDOUT_LOG" "$STDERR_LOG" 2>/dev/null || log_err "no logs yet"
    else
        tail -n 100 "$STDOUT_LOG" "$STDERR_LOG" 2>/dev/null || log_err "no logs yet"
    fi
}

case "${1:-}" in
    start)   cmd_start ;;
    stop)    cmd_stop ;;
    restart) cmd_stop || true; cmd_start ;;
    status)  cmd_status ;;
    log)     shift; cmd_log "${1:-}" ;;
    *) echo "Usage: $0 {start|stop|restart|status|log [-f]}" >&2; exit 2 ;;
esac
