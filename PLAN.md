# Phase 3 (V1.5) Implementation Plan

<!-- GateGuard: New file. Importers: none (plan doc only). Affected API: none. Data schemas: none. User instruction: "开始阶段3" — implement V1.5 differentiation per enhancement doc. -->

## Goal: Build differentiation moat per enhancement doc V1.5

Current state: v0.2.0 with 210 tests, 9 submodules, 13 CLI commands, ruff clean, CI green.

## V1.5 Requirements (from enhancement doc)

1. **fusion-mlx deep integration** — session-level model switching, model auto-recommendation
2. **fusion-multi-nodes cluster scheduling** — task dispatch to cluster nodes, node health monitoring
3. **Enterprise audit system** — operation log search, compliance report export
4. **Incremental snapshot optimization** — delta compression, storage stats, auto-cleanup
5. **Private MCP plugin platform** — plugin registry, lifecycle management, marketplace

## New Modules to Implement

### Module 1: `cluster/` — Distributed Cluster Scheduling
**Files:**
- `cluster/__init__.py` — exports
- `cluster/scheduler.py` — ClusterScheduler class
  - `discover_nodes()` — discover cluster nodes via fusion-multi-nodes API
  - `dispatch_task(session_id, target_node)` — dispatch session to remote node
  - `get_node_status()` — fetch all node health/load
  - `auto_schedule(task_requirements)` — auto-pick best node based on load
  - `migrate_session(session_id, from_node, to_node)` — live session migration
- `cluster/node_client.py` — NodeClient for HTTP communication with cluster nodes
  - `health_check()` — check node availability
  - `submit_task()` — submit task to remote node
  - `get_task_status()` — poll task progress
  - `fetch_result()` — retrieve completed task result
- `cluster/sync.py` — SessionSyncManager
  - `push_snapshot(node, snapshot_id)` — push snapshot to remote node
  - `pull_snapshot(node, snapshot_id)` — pull snapshot from remote node
  - `sync_project(node, project_dir)` — sync project files

### Module 2: `audit/` — Enterprise Audit System
**Files:**
- `audit/__init__.py` — exports
- `audit/logger.py` — AuditLogger class
  - `log_operation(action, target, actor, details)` — structured audit log entry
  - `search(query, filters)` — search audit logs with filters (date range, action type, actor, target)
  - `export_report(format, filters)` — export compliance report (JSON/CSV/Markdown)
  - `get_statistics(start_date, end_date)` — aggregate audit statistics
- `audit/models.py` — AuditEntry, AuditFilter, AuditReport dataclasses
- `audit/store.py` — AuditStore
  - JSONL file persistence (extends sandbox/audit.py pattern)
  - Rotation and retention policy
  - Index for fast search

### Module 3: `plugin/` — MCP Plugin Platform
**Files:**
- `plugin/__init__.py` — exports
- `plugin/registry.py` — PluginRegistry class
  - `register(plugin_manifest)` — register a plugin
  - `unregister(plugin_id)` — remove plugin
  - `list_plugins(category)` — list available plugins
  - `search_plugins(query)` — search marketplace
  - `install(plugin_id)` — install plugin from marketplace
  - `update(plugin_id)` — update installed plugin
- `plugin/manager.py` — PluginManager class
  - `load(plugin_id)` — load plugin into runtime
  - `unload(plugin_id)` — unload plugin
  - `execute(plugin_id, action, params)` — execute plugin action
  - `get_plugin_status()` — runtime status of all loaded plugins
- `plugin/models.py` — PluginManifest, PluginCategory, PluginStatus dataclasses

### Module 4: Enhanced `core/` — Model Dual-Stack Scheduling
**Enhance existing files:**
- `core/config.py` — add dual-stack model config (local MLX + cloud API)
  - `DualModelConfig` with `local_model` + `cloud_model` + `routing_strategy`
  - `ModelRouter` — auto-select model based on task complexity
- `core/client.py` — add `DualStackClient`
  - Wraps MLXClient with cloud fallback
  - `smart_chat()` — auto-route to appropriate model stack
  - `switch_model(stack)` — explicit stack switching

### Module 5: Enhanced `snapshot/` — Incremental Optimization
**Enhance existing files:**
- `snapshot/manager.py` — add:
  - `get_storage_stats()` — disk usage, snapshot count, delta sizes
  - `auto_cleanup(max_age_days, max_snapshots)` — retention policy
  - `compress_snapshot(snapshot_id)` — compress old snapshots
  - `verify_snapshot(snapshot_id)` — integrity verification

## CLI Extensions

New subcommands:
- `cluster <action>` — discover/dispatch/status/schedule/migrate
- `audit <action>` — log/search/export/stats
- `plugin <action>` — list/install/unload/execute/search

Enhanced existing:
- `session create --node <node_id>` — create session on specific cluster node
- `snapshot create --compress` — create compressed snapshot
- `snapshot cleanup --max-age 30 --max-count 50` — auto-cleanup

## Version Bump: 0.2.0 → 0.3.0

## Implementation Order

1. **audit/** — Enterprise audit (independent, no external deps, extends existing sandbox audit)
2. **core/ enhancement** — Dual-stack model config + ModelRouter
3. **snapshot/ enhancement** — Storage stats, auto-cleanup, compress, verify
4. **plugin/** — MCP plugin platform
5. **cluster/** — Distributed cluster scheduling (depends on core enhancement)
6. **CLI extensions** — Wire up all new modules
7. **Tests** — Full test coverage for all new code
8. **README/docs update** — Reflect new capabilities
9. **CI/lint** — Ensure all green

## Estimated Scope

- ~5 new module files + 4 enhanced files
- ~50-60 new tests
- 3 new CLI subcommands + enhancements to existing ones
- Version 0.3.0
