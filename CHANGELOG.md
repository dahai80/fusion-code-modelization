# Changelog

All notable changes to fusion-code-modelization are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/).

## [0.7.5] — 2026-10-28

### Fixed

- **Process title (#34)**: the REST API server process now shows as `fusion-code-modelization serve :<port>` in `ps`/Activity Monitor instead of bare `Python`. Implemented via `fusion_core.set_process_title()` (setproctitle with try/except fallback) at the single `run_server()` entrypoint, which covers `start.sh`, `fusion-code-modelization serve`, and `python -m fusion_code_modelization.server`. `setproctitle` is inherited from the fusion-core dependency; start.sh PID/kill/health logic unaffected (verified live).

### Changed

- **Single-point config resolution (#35)**: API-key resolution now delegates to `fusion_core.config.client_key()` (config-conventions Phase 2.2) instead of hand-rolled `_resolve_api_key()` / `_resolve_server_api_key()`. Resolution order: `FUSION_CLIENT_KEY` → `FUSION_MLX_API_KEY` (deprecated alias, warns) → `MLX_API_KEY` (deprecated alias, warns); dev missing key = empty + warning, `FUSION_PROFILE=prod` missing key = `RuntimeError`. The REST server's client-auth token and the gateway client key are now the same secret (`FUSION_CLIENT_KEY`); `FUSION_SERVER_API_KEY` is no longer consulted. `scripts/check-env.py` reports 0 findings for this repo; `grep 'def _resolve.*key'` returns nothing.

### Docs

- README / README_CN / docs/operations.md updated to `FUSION_CLIENT_KEY` (removed the `fg-admin-key` placeholder example — audit 1025 §1.5 repeat offender).

### Fixed

- **CI-reality governance false positive (#33)**: verified against the live repo that GitHub Actions is enabled (`allowed_actions: all`) with 39 recorded runs — the survey's "Actions disabled / workflows never executed" finding came from a jq bug (`.runs` vs `workflow_runs` → null misread as 404). Latest run on the v0.7.3 commit (9b41f96) is green across all 5 jobs and exercises the CLI smoke suite (`test_cli_smoke.py`, 46 tests). No code changes; verification-only patch release.

### Removed

- Stale remote branch `fix/backlog-27-31` (leftover tracking ref from squash-merged PR #32).

## [0.7.3] — 2026-10-26

### Fixed

- **Snapshot data loss (#27)**: snapshots now persist full file contents; restoring a first snapshot no longer blanks every file, chained snapshots restore each historical state exactly, and files created after a snapshot are deleted on restore.
- **Analyzer language coverage (#30)**: dependency import extraction extended from 7 to 14 languages (Rust, PHP, Ruby, Swift, Kotlin, Scala, COBOL added). Dead-code detection no longer flags files in languages without import extraction (TypeScript, VB6) as dead — new `dead_code_report()` reports them as *undetermined*, and `estimate_tech_debt` gains `undetermined_files`.
- **Hook coverage gaps (#28)**: plain (non-loop) CLI LLM paths (transpile/refactor/test-gen/security/doc-gen/workflow-decompose) now emit POST_LLM (secret scrub + guard verdicts); `SafeWriter` bridges async PRE_WRITE handlers in sync paths instead of skipping them; `--output` strict path containment. GuardBridge degrades to builtin regex fallback when the optional fusion-guard service is unreachable.
- **Docs over-claims (#29)**: README/README_CN state only verifiable capabilities — local plugin registry (not MCP), local git ops + PR description generation (no Gitee/GitLab/GitHub APIs), no changelog generation, no OPENAI_API_KEY fallback; language matrix documents actual coverage (import extraction 14 langs, static security 3 langs, TS/VB6 undetermined).

### Added

- **Real benchmark measurements (#31)**: `benchmark run --suite code_quality --path <dir>` now measures max cyclomatic complexity (AST), test coverage (pytest --cov), and lint violations (ruff). `BenchmarkItem` gains `lower_is_better`; runner status and report comparison respect metric direction.

### Tests

- 894 tests pass (up from 877); ruff clean.

## [0.7.2] — 2026-10-25

### Fixed

- **5 broken CLI command groups** (runtime crashes from field/method-name mismatches, all exposed by the new smoke suite; closes #25):
  - `sandbox check` — called nonexistent `SandboxGuard.check_path`; now uses `check_read` and exits 0 (allowed) / 1 (denied)
  - `snapshot create/list/rewind` — `snap.id`/`s['id']` → `snapshot_id` (real model field)
  - `memory init/list/load/query` — wrong signatures (`list_directory_memories(path)` takes no args, `MemoryContext(tier_manager=...)` kwarg doesn't exist); manager now constructed with `project_dir`, handlers use real APIs
  - `benchmark run/history` — `passed_count`/`average_score` → `passed_items`/`avg_score`; history keys → `avg_score`/`pass_rate`
  - `loadbalancer rebalance` — read dict keys from `SchedulingDecision` objects that don't exist; now prints `reason` + `selected_node`

### Added

- **CLI smoke suite** (`tests/test_cli_smoke.py`, 46 tests): every registered subcommand gets `--help` (exit 0) plus one representative real invocation each (LLM mocked, filesystem fixtures in tmp); structurally prevents shipping a subcommand that crashes on first invocation. Includes the issue-#25 grep gate (`guard.check_path` must not reappear).
- **benchmark real measurement**: `benchmark run --path <dir>` now computes a real `syntax_correctness` score (py_compile pass rate over project `.py` files) instead of always producing all-SKIPPED reports; without `--path` the report states explicitly that no measurements ran.

### Changed

- **audit wiring**: the `audit_log` hook guard (POST_EXEC) now persists to the AuditLogger JSONL store (`.fusion/audit/`) instead of only logging — pipeline git operations audited at hooks.py `audit_log`; persistence failure is non-blocking (hook remains allow-through).
- **trace wiring**: `PipelineIntegrator.create_pr` now records a `code_change` trace node per created PR branch (integrator.py `create_pr`), so pipeline PRs land in the traceability graph without manual `trace create`.

## [0.7.1] — 2026-09-02

### Added

- **Operations guide** (`docs/operations.md`): production deployment runbook (pre-flight CI gate, standard update, rollback, first-time install, health-check gate), secret management & rotation procedure (90-day schedule, 6-step zero-downtime rotation, systemd EnvironmentFile storage, compromise response), and monitoring dashboard (`/metrics` panel mapping, 15s scrape script, 4 alerting rules).

### Changed

- **77 audit findings resolved** (9 CRITICAL / 24 HIGH / 25 MEDIUM / 19 LOW) across Architecture, Security, Performance, Enterprise-readiness, and Operations dimensions.
- **Security**: hook layer hardened to fail-closed (unknown action → DENY); symlink traversal blocked in snapshot/scan; WebSocket + REST body-size limits (`FUSION_MAX_BODY_BYTES`); CORS/Host guard middleware reordered to reject oversized bodies + misdirected hosts before auth budget spent (413/421); secret scrubbing widened; non-loopback node http flagged; LLM JSON schema-validated before CLI/API return.
- **Correctness**: `MemoryContext.summarize/query` returns `str` per `chat()` contract (was returning raw dict); stream path empty-content guard (issue #14 extended); agent loop fail-fast on unknown tool; retry total_deadline cap.
- **Performance**: snapshot scan size cap + ignore list (build/dist/target); scheduler state incremental save.
- **Type safety**: mypy 18 → 0 errors; bandit CI gating enforced (no `|| true`); ruff clean; bandit 0 issues all severities (4 Low eliminated — 3 nosec + 1 real `assert` → explicit None-narrowing).
- **Tests**: 826 tests pass, 82% coverage; `TestServerGuards` (413/421/CORS-null), `TestServerLifespan` (restore/persist, bad-json warn), `test_safe_writer.py` (11 path-traversal + hook tests).

### Fixed

- **conftest key-strip bug**: `pytest_configure` used substring check (`"live" not in "not live"` = False) that leaked shell `FUSION_MLX_API_KEY` into mocked tests, enabling auth by accident → 17-test regression. Fixed to `is_live_only = markexpr == "live"`.
- **Live gateway probe** skipped (401): probe + tests now send `Bearer` header; default model switched to `Qwen3.8-27B-4bit` (loaded model; `Qwen3.5-9B-4bit` not loaded → 502).
- **Live E2E transpile** verified: python → go via Qwen3.8-27B-4bit, go-vet clean.

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
