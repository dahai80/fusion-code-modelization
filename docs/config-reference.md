---
doc_id: fusion-code-modelization/config-reference
product: fusion-code-modelization
class: app
entry: service
doc_type: config-reference
title: {zh: "Fusion-Code-Modelization 配置参考", en: "Fusion-Code-Modelization Config Reference"}
audience: engineer
status: draft
version: 0.7.5
updated: 2026-11-07
owner: "@dahai"
source_of_truth:
  - fusion_code_modelization/core/config.py
  - fusion_code_modelization/server/app.py
  - fusion_code_modelization/server/runner.py
  - start.sh
---

# Fusion-Code-Modelization 配置参考 / Config Reference

全部配置经环境变量；代码内定义于 `core/config.py`（LLM 客户端）、`server/app.py`（服务边界）、`server/runner.py`（日志）、`start.sh`（生命周期）。无配置文件。

## 环境变量

| Env var | Default | Effect |
|---|---|---|
| `FUSION_GATEWAY_URL` | `http://localhost:11432/v1` | fusion-gateway OpenAI-compatible base URL; all LLM calls route here |
| `FUSION_MODEL_ID` | `Qwen3.5-9B-4bit` | Model id sent to the gateway |
| `FUSION_TIMEOUT` | `120.0` | LLM request timeout (seconds) |
| `FUSION_RETRY_ATTEMPTS` | `2` | Retry attempts for LLM requests |
| `FUSION_FCM_HOST` | `127.0.0.1` | REST server bind host (start.sh) |
| `FUSION_FCM_PORT` | `11459` | REST server port (start.sh); port registered in monorepo `architecture/port-registry.yaml` |
| `FUSION_LOG_LEVEL` | `INFO` | Server log level (`runner.py`, upper-cased) |
| `FUSION_MAX_BODY_BYTES` | `1048576` | Request body size cap (1 MiB); larger bodies are rejected |
| `FUSION_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Comma-separated allowed Host/Origin values for the server |
| `FUSION_CLIENT_KEY` | (empty in dev) | Client-auth token; resolved via `fusion_core.config.client_key()` — same secret the gateway accepts |

## 解析语义 / Resolution semantics

- key 解析是 fusion-core 单点：`FUSION_CLIENT_KEY` → `FUSION_MLX_API_KEY`（旧名，warn）→ `MLX_API_KEY`（旧名，warn）。dev 缺失 = 空串 + 一次性 warn；`FUSION_PROFILE=prod` 缺失 = `RuntimeError`。
- 端口/host 变量只被 `start.sh` 消费；直接 `python -m fusion_code_modelization.server --host --port` 时以命令行为准。
- 日志级别仅影响 server 进程（`FUSION_LOG_LEVEL`），CLI 输出不受它控制。

## 约定 / Constraints

- `FUSION_MAX_BODY_BYTES` 是 DoS 边界的一部分：放大它等于放宽请求体上限，需同时评估内存。
- `FUSION_ALLOWED_HOSTS` 增加条目即放宽 Host/Origin 校验；不要设为 `*`。
- 服务端口变更须先改 monorepo `architecture/port-registry.yaml`，再改本处默认值。
