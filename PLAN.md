# Phase 4 (V2.0) Implementation Plan

<!-- GateGuard: Updated file. Importers: dev planning. Affected API: none. Data schemas: none. User instruction: "启动下一个阶段的实施" — implement V2.0 per enhancement doc. -->

## Goal: Build V2.0 unique ecosystem moat per enhancement doc

Current state: v0.3.0 with 327 tests, 14 submodules, 16 CLI commands, ruff clean, CI green.

## V2.0 Requirements (from enhancement doc Section 7 — 长期版本)

1. **内置自动化测试 & 性能基准评测闭环** — Auto-test execution + benchmark scoring
2. **集群智能负载均衡** — Auto-distribute tasks to idle nodes, smart scheduling
3. **完整内网离线部署方案** — Offline mode, air-gapped deployment for enterprise
4. **Fusion 全链路统一追踪** — End-to-end traceability: requirement → code → test artifact
5. **Agent 跨机器通信协同** — Cross-node agent collaboration for mega-scale refactoring

## New Modules to Implement

### Module 1: `benchmark/` — Performance Benchmark & Test Loop
**Files:**
- `benchmark/__init__.py` — exports
- `benchmark/models.py` — BenchmarkSuite, BenchmarkResult, BenchmarkReport dataclasses
  - `BenchmarkSuite` — named benchmark collection with target metrics
  - `BenchmarkResult` — single benchmark run result (score, duration, pass/fail, metrics dict)
  - `BenchmarkReport` — aggregated report with summary statistics, pass rate, trend comparison
- `benchmark/runner.py` — BenchmarkRunner class
  - `run_suite(suite_name)` — execute all benchmarks in a suite
  - `run_single(benchmark_id)` — execute single benchmark
  - `compare_reports(report_a, report_b)` — compare two runs, show regressions/improvements
  - `get_historical_trends(suite_name, limit)` — trend analysis over last N runs
- `benchmark/suite.py` — PredefinedBenchmarkSuites
  - Code quality metrics (complexity, duplication, coverage)
  - Performance metrics (inference latency, throughput, memory)
  - Migration quality metrics (syntax correctness, semantic preservation)

### Module 2: `loadbalancer/` — Intelligent Cluster Load Balancer
**Files:**
- `loadbalancer/__init__.py` — exports
- `loadbalancer/models.py` — LoadMetric, SchedulingDecision, BalancerConfig dataclasses
  - `LoadMetric` — cpu/mem/gpu usage, active_tasks, weight
  - `SchedulingDecision` — selected_node, reason, alternatives, estimated_wait
  - `BalancerConfig` — strategy, thresholds, cooldown
- `loadbalancer/strategy.py` — LoadBalanceStrategy enum + strategy implementations
  - `ROUND_ROBIN` — simple round-robin across nodes
  - `LEAST_LOADED` — pick node with lowest load_score
  - `WEIGHTED_CAPACITY` — weight by hardware specs
  - `AFFINITY_BASED` — session affinity, reuse same node when possible
- `loadbalancer/balancer.py` — LoadBalancer class
  - `evaluate_cluster()` — collect metrics from all cluster nodes
  - `select_node(task_requirements)` — pick optimal node for a task
  - `rebalance()` — redistribute tasks if cluster state changed
  - `get_cluster_overview()` — dashboard-ready cluster health summary
  - `predict_capacity(duration_hours)` — forecast cluster capacity

### Module 3: `offline/` — Offline / Air-Gapped Deployment
**Files:**
- `offline/__init__.py` — exports
- `offline/models.py` — OfflineMode, OfflineCapability, OfflinePackage dataclasses
  - `OfflineMode` — FULL_OFFLINE / SEMI_OFFLINE / ONLINE enum
  - `OfflineCapability` — what's available in each mode (local_model, cluster, audit, etc.)
  - `OfflinePackage` — bundled model + plugin + config for air-gapped install
- `offline/manager.py` — OfflineManager class
  - `detect_mode()` — auto-detect network state, determine offline level
  - `prepare_offline_package(output_dir)` — bundle models, plugins, configs into deployable package
  - `restore_from_package(package_dir)` — install from offline package
  - `get_available_capabilities()` — list what works in current mode
  - `validate_package(package_dir)` — verify package integrity before install
- `offline/cache.py` — OfflineCache
  - `cache_model(model_id)` — download and cache model for offline use
  - `cache_plugin(plugin_id)` — cache plugin for offline install
  - `list_cached()` — show all cached resources
  - `cleanup_cache(max_size_mb)` — evict oldest cached items

### Module 4: `trace/` — End-to-End Traceability
**Files:**
- `trace/__init__.py` — exports
- `trace/models.py` — TraceNode, TraceEdge, TraceChain, TraceReport dataclasses
  - `TraceNode` — a traceable artifact (requirement, code change, test result, deployment)
  - `TraceEdge` — link between two nodes with relationship type
  - `TraceChain` — full trace path from source to destination
  - `TraceReport` — aggregated traceability report with coverage metrics
- `trace/tracker.py` — TraceTracker class
  - `create_node(artifact_type, artifact_id, metadata)` — register a traceable artifact
  - `link_nodes(source_id, target_id, relationship)` — create trace link
  - `trace_forward(artifact_id)` — trace forward from requirement to all downstream
  - `trace_backward(artifact_id)` — trace backward from test/deployment to origin
  - `get_trace_chain(artifact_id, direction)` — full chain in either direction
  - `generate_report(filters)` — traceability coverage report
- `trace/store.py` — TraceStore
  - JSONL persistence for trace nodes and edges
  - Graph traversal for forward/backward tracing
  - Search and filter by artifact type, timestamp, metadata

### Module 5: `agent_comm/` — Cross-Node Agent Communication
**Files:**
- `agent_comm/__init__.py` — exports
- `agent_comm/models.py` — AgentMessage, AgentChannel, CollaborationTask dataclasses
  - `AgentMessage` — structured inter-agent message (sender, recipient, type, payload)
  - `AgentChannel` — named communication channel between agents
  - `CollaborationTask` — multi-agent collaborative task with role assignments
- `agent_comm/channel.py` — AgentChannelManager
  - `create_channel(name, participants)` — set up communication channel
  - `send_message(channel, message)` — send message to channel
  - `receive_messages(channel, agent_id)` — get pending messages for agent
  - `close_channel(name)` — tear down channel
- `agent_comm/coordinator.py` — CollaborationCoordinator
  - `create_collaboration(task_description, agents)` — set up multi-agent collaboration
  - `assign_roles(collaboration_id)` — auto-assign roles based on agent capabilities
  - `monitor_progress(collaboration_id)` — track collaboration status
  - `merge_results(collaboration_id)` — collect and merge all agent outputs
  - `handle_conflict(collaboration_id, conflict_type)` — resolve cross-agent conflicts

## Enhance Existing Modules

### Enhanced `cluster/scheduler.py` — Integrate LoadBalancer
- Add `smart_dispatch()` method that uses LoadBalancer for node selection
- Add `cluster_health_report()` method leveraging LoadBalancer.get_cluster_overview()

### Enhanced `core/config.py` — Offline Mode Support
- Add `OfflineConfig` dataclass with mode, cache_dir, fallback_behavior
- Add `get_runtime_config()` that respects offline mode restrictions

### Enhanced `pipeline/__init__.py` — Trace Integration
- Add `create_trace_link(source, target, relationship)` — link pipeline artifacts
- Add `get_traceability_report()` — trace report for pipeline runs

## CLI Extensions

New subcommands:
- `benchmark <action>` — run/compare/trends/suites
- `loadbalancer <action>` — evaluate/select/overview/predict
- `offline <action>` — detect/prepare/restore/capabilities/validate
- `trace <action>` — create/link/forward/backward/report
- `agent-comm <action>` — channel/send/receive/collaborate/monitor

## Version Bump: 0.3.0 → 0.4.0

## Implementation Order

1. **benchmark/** — Test & benchmark loop (independent, pure local logic)
2. **loadbalancer/** — Intelligent load balancing (enhances cluster)
3. **offline/** — Offline deployment (cross-cutting, affects core/config)
4. **trace/** — End-to-end traceability (standalone graph engine)
5. **agent_comm/** — Cross-node agent communication (depends on cluster)
6. **Enhance existing** — Wire loadbalancer into cluster, offline into core, trace into pipeline
7. **CLI extensions** — Wire up all new modules
8. **Tests** — Full test coverage for all new code
9. **README/docs update** — Reflect new capabilities
10. **CI/lint** — Ensure all green

## Estimated Scope

- ~15 new module files + 3 enhanced files
- ~60-80 new tests
- 5 new CLI subcommands
- Version 0.4.0
