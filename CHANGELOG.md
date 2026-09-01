# Changelog

All notable changes to fusion-code-modelization are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/).

## [0.7.0] — 2026-09-01

### Added

- **M1 — Agent Loop self-heal engine** (`core/agent_loop.py`): bounded (max_iter) + fully JSONL-traced
  self-heal loop. The model decides *how to fix*, not *which tool* — tool sequence stays fixed, preserving
  determinism and auditability. Wired into `transpile --loop`, `refactor --loop`, `test-gen --loop` with
  per-domain verify tools (logic-equivalence / dual-run equivalence / syntax check).
  - CLI flags: `--loop` (enable self-heal), `--max-iter` (default 5).
  - New APIs: `AgentLoop`, `LoopTool`, `LoopToolResult`, `LoopTrace`, `LoopStatus`.
  - `*_with_loop()` methods on `CodeTranspiler`, `IncrementalRefactorer`, `UnitTestGenerator`.

- **M2 — Hook deterministic interception layer** (`core/hooks.py`): runtime interception the model cannot
  bypass. Event bus with 4 events (`PRE_WRITE` / `POST_LLM` / `PRE_EXEC` / `POST_EXEC`), registry with
  `allow` / `deny` / `modify` decisions, and built-in guards: `path_guard` (path traversal + system dirs),
  `dangerous_cmd_guard` (`rm -rf /`, fork bomb, `mkfs`, etc.), `secret_scrub` (AWS keys, `sk-*`, `ghp_*`,
  private keys), `audit_log`.
  - `GuardBridge` delegates deny/redact decisions to `fusion-core.guard_client` → fusion-guard (UDS
    JSON-RPC). Graceful degrade with `WARNING` log + regex fallback when guard unavailable.
  - Wired into `AgentLoop` (POST_LLM + PRE_EXEC emit points) and CLI (`--no-hooks` global flag).
  - New APIs: `HookEvent`, `HookAction`, `HookDecision`, `HookHandler`, `HookRegistry`, `GuardBridge`,
    `default_registry`, built-in guards.

### Tests

- `tests/test_agent_loop.py` — 14 tests (loop core, refactor/transpile/test-gen with loop).
- `tests/test_hooks.py` — 28 tests (built-in guards, registry, default_registry, GuardBridge,
  AgentLoop hook integration).
- Suite: 775 tests green, coverage 84% total (hooks 91%, agent_loop 92%).

### Changed

- `transpile_with_loop` / `refactor_with_loop` / `generate_with_loop` accept optional `hooks` param.
- `core/__init__.py` exports Hook API.

### Known Issues

- Live local inference through fusion-gateway blocked by upstream routing gap (local MLX model ids fall
  to `cloud_default` fallback → 400). Tracked in fusion-gateway#145. Loop + hook mechanics verified via
  mocked HTTP and partial live run (retry → max_iter → partial result, hooks wired, no false deny).

## [0.6.5] — 2026-08

- Server default port 11441 → 11459 (#16, #17).
- Cluster D-H3 guard: empty submit_task content → failed (#14, #15).
- Adopt fusion-core http_client (pool + retry) + D-H3 empty content guard (#13).

## [0.6.4]

- Route all inference through fusion-gateway (11432), no direct fusion-mlx (#11).

## [0.6.3]

- MLXClient auth header + correct default model id (#8, #9).
