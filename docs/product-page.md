---
doc_id: fusion-code-modelization/product-page
product: fusion-code-modelization
class: app
entry: service
doc_type: product-page
title: {zh: "Fusion-Code-Modelization 产品页", en: "Fusion-Code-Modelization Product Page"}
audience: engineer
status: draft
version: 0.7.5
updated: 2026-11-07
owner: @dahai
source_of_truth:
  - README.md
  - pyproject.toml
  - start.sh
  - fusion_code_modelization/server/app.py
---

# Fusion-Code-Modelization 产品页 / Product Page

Fusion-Code-Modelization 是本地优先的遗留代码现代化与跨语言迁移工具集，由 fusion-mlx 驱动。两种形态：REST API 服务（默认 `127.0.0.1:11459`，会话/工作流/集群调度）与 CLI（`fusion-code-modelization`，22 个子命令：analyze / transpile / refactor / test-gen / security / session / snapshot / workflow 等）。所有 LLM 调用走 fusion-gateway（`FUSION_GATEWAY_URL`，默认 `http://localhost:11432/v1`），本仓库不直接 import MLX。

Fusion-Code-Modelization is a local-first legacy-code modernization and cross-language migration toolkit powered by fusion-mlx. Two forms: a REST API service (default `127.0.0.1:11459`; sessions, workflows, cluster scheduling) and a CLI (`fusion-code-modelization`, 22 subcommands: analyze / transpile / refactor / test-gen / security / session / snapshot / workflow and more). All LLM calls go through fusion-gateway (`FUSION_GATEWAY_URL`, default `http://localhost:11432/v1`); this repo never imports MLX directly.

## App block

```yaml
app:
  surface:              # 对外形态 / what you integrate with
    - REST API on 127.0.0.1:11459 (start.sh or `fusion-code-modelization serve`)
    - CLI `fusion-code-modelization` (22 subcommands)
    - WebSocket /ws/chat for streaming sessions
  builds_on:            # 依赖 / dependencies
    - fusion-gateway (:11432, /v1 OpenAI-compatible endpoints)
    - fusion-core (set_process_title, client_key config resolution)
    - httpx + pydantic (only hard runtime deps)
  hosts:                # 托管的状态 / state owned
    - session state and workflow plans behind the REST API
    - incremental snapshots (snapshot/rollback) and project memory (FUSION.md three-tier)
  integration_surface:  # 接入面 / contract
    - POST /api/workflows/run, GET /api/workflows/{plan_id}
    - /api/sessions (create, chat, distribute, merge, cluster-status)
    - GET /health (liveness), GET /metrics, WS /ws/chat
  extension_points:     # 扩展点 / where to extend
    - plugin system (local registry + lifecycle, `fusion-code-modelization plugin`)
    - workflow node decomposition (`workflow` subcommand, dynamic task split)
    - benchmark suites (custom report comparison, `benchmark` subcommand)
```

## 核心能力 / Core capabilities

### 1. 代码分析与跨语言转译 / Analysis + transpilation

用户不再自己写：依赖图分析器、语言识别、逐文件转译循环与 LLM prompt 拼装。`analyze` 输出代码库依赖关系；`transpile` 在语言间转译（LLM 经 fusion-gateway）。约束：转译质量取决于上游模型（默认 `Qwen3.5-9B-4bit`，`FUSION_MODEL_ID` 覆盖）；产物是建议不是保证——必须配合测试与人工评审，不要无人监督直合主干。

What you no longer write: dependency-graph analyzers, language detection, per-file transpilation loops and prompt plumbing. Constraints: quality depends on the upstream model (default `Qwen3.5-9B-4bit`, override with `FUSION_MODEL_ID`); output is a proposal, not a guarantee — gate it with tests and review.

### 2. 增量重构与会话隔离 / Incremental refactor + session isolation

用户不再自己写：重构进度的断点续跑、并行会话的创建/分发/合并、会话级 chat 上下文管理。`refactor` 增量推进；`session` 管理并行会话（`/api/sessions/{id}/distribute` 与 `/merge` 服务端编排）。约束：会话状态在服务进程内——重启服务前先确认无进行中的会话；多机分布用 `cluster` / `loadbalancer` 子命令，不要手工复制状态。

What you no longer write: resumable refactor progress, parallel session create/distribute/merge, per-session chat context. Constraints: session state lives in the server process — check for in-flight sessions before restarting; use `cluster` / `loadbalancer` for multi-node, do not hand-copy state.

### 3. 快照与回滚 / Snapshots and rollback

用户不再自己写：重构前的代码快照、失败回滚、增量快照存储。`snapshot` 子命令提供增量快照与回滚（0.7.x 修复过快照数据丢失问题 #27-#31）。约束：回滚覆盖工作区文件——执行前确认未提交的修改已保存；快照是本机数据，不进 git，不跨机器同步。

What you no longer write: pre-refactor code snapshots, failure rollback, incremental snapshot storage. Constraints: rollback overwrites working-tree files — save uncommitted work first; snapshots are local data, not in git and not synced across machines.

### 4. 安全扫描与沙箱 / Security scan + sandbox

用户不再自己写：漏洞模式扫描、生成代码的沙箱执行与审计流水。`security` 扫描安全漏洞；`sandbox` 提供安全沙箱与审计；`audit` 提供企业审计记录。约束：沙箱是本机隔离手段不是权限边界——不要用沙箱运行不受信任的第三方代码；审计日志默认落本机。

What you no longer write: vulnerability pattern scans, sandboxed execution of generated code, audit trails. Constraints: the sandbox is local isolation, not a security boundary — do not run untrusted third-party code in it; audit logs stay on the machine.

### 5. 工作流编排 / Workflow orchestration

用户不再自己写：任务分解、DAG 化执行、进度查询。`POST /api/workflows/run` 提交计划，`GET /api/workflows/{plan_id}` 轮询；CLI `workflow` 支持动态分解。约束：工作流内的 LLM 步骤都经 fusion-gateway——网关不可达时步骤失败可见（`FUSION_TIMEOUT` 默认 120s，`FUSION_RETRY_ATTEMPTS` 默认 2）；超大任务先 `decompose` 出微服务边界再编排。

What you no longer write: task decomposition, DAG execution, progress polling. Constraints: every LLM step goes through fusion-gateway — gateway outage fails steps visibly (`FUSION_TIMEOUT` 120s, `FUSION_RETRY_ATTEMPTS` 2 by default); run `decompose` first for very large tasks.

## 边界 / Non-goals

- 不做模型推理：推理在 fusion-mlx / fusion-gateway；本仓库只是 HTTP 客户端。
- 不承诺转译产物可直接上生产：始终经过测试与评审。
- 不做多租户：单机单用户工具，服务无租户概念。

No inference here (that is fusion-mlx / fusion-gateway; this repo is an HTTP client), no promise that transpiled output is production-ready (always gate with tests and review), no multi-tenancy (single-user local tool).
