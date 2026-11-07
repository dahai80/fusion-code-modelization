---
doc_id: fusion-code-modelization/api-reference
product: fusion-code-modelization
class: app
entry: service
doc_type: api-reference
title: {zh: "Fusion-Code-Modelization API 参考", en: "Fusion-Code-Modelization API Reference"}
audience: engineer
status: draft
version: 0.7.5
updated: 2026-11-07
owner: "@dahai"
source_of_truth:
  - fusion_code_modelization/server/app.py
  - fusion_code_modelization/cli/__init__.py
  - docs/api.md
---

# Fusion-Code-Modelization API 参考 / API Reference

REST 服务由 `python -m fusion_code_modelization.server`（或 `start.sh` / `fusion-code-modelization serve`）启动，FastAPI app 定义在 `fusion_code_modelization/server/app.py`。逐模块的 Python API 见 `docs/api.md`，本文件列 HTTP/WS 契约与 CLI 子命令，以源码为准。

## REST 端点（默认 127.0.0.1:11459）

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + dependency checks (gateway reachability, disk); 200 when healthy |
| GET | `/metrics` | Process/runtime metrics |
| GET | `/api/sessions` | List sessions |
| POST | `/api/sessions` | Create a session; body `SessionCreateRequest {name: str = "unnamed"}` |
| GET | `/api/sessions/{session_id}` | Session detail |
| POST | `/api/sessions/{session_id}/chat` | Send a chat turn to the session (LLM via gateway); body `ChatRequest` |
| POST | `/api/sessions/{session_id}/distribute` | Distribute session work (cluster) |
| GET | `/api/sessions/{session_id}/cluster-status` | Cluster progress for the session |
| POST | `/api/sessions/{session_id}/merge` | Merge distributed results |
| POST | `/api/sessions/{session_id}/{action}` | Generic session action (`delete` deletes the session) |
| POST | `/api/workflows/run` | Submit a workflow plan; body `WorkflowRunRequest` |
| GET | `/api/workflows/{plan_id}` | Poll workflow plan status |
| WS | `/ws/chat` | Streaming chat WebSocket |

中间件：请求体大小上限 `FUSION_MAX_BODY_BYTES`（默认 1 MiB）；Origin/Host 校验基于 `FUSION_ALLOWED_HOSTS`（默认 `127.0.0.1,localhost`）。错误响应 `{detail: ...}`。

## CLI 子命令（`fusion-code-modelization <sub>`）

`analyze`（path + `--output`） · `transpile` · `refactor` · `test-gen` · `security` · `session` · `snapshot` · `workflow` · `memory`（FUSION.md 三层项目记忆） · `sandbox` · `decompose`（微服务边界检测） · `doc-gen` · `audit` · `cluster` · `plugin` · `version` · `serve`（启动 REST 服务） · `benchmark` · `loadbalancer` · `offline`（离线部署管理） · `trace`（端到端追溯） · `agent-comm`（agent 跨机通信）

5 个核心子命令支持 `--stream`（流式输出）。

## 服务进程

- 入口唯一：`run_server()`（`start.sh`、`serve`、`python -m` 三种方式都汇到这里），进程标题 `fusion-code-modelization serve :<port>`（经 `fusion_core.set_process_title`）。
- PID 文件 `.fusion-code-modelization.pid`；日志 `logs/stdout.log` + `logs/stderr.log`。
- API key 解析委托 `fusion_core.config.client_key()`（`FUSION_CLIENT_KEY`），服务端鉴权 token 与网关 client key 是同一个密钥。
