---
doc_id: fusion-code-modelization/troubleshooting
product: fusion-code-modelization
class: app
entry: service
doc_type: troubleshooting
title: {zh: "Fusion-Code-Modelization 故障排查", en: "Fusion-Code-Modelization Troubleshooting"}
audience: engineer
status: draft
version: 0.7.5
updated: 2026-11-07
owner: "@dahai"
source_of_truth:
  - start.sh
  - fusion_code_modelization/server/app.py
  - docs/operations.md
---

# Fusion-Code-Modelization 故障排查 / Troubleshooting

## 服务起不来 / Server fails to start

1. `start.sh start` 报 `process exited early` → 看 `logs/stderr.log`。常见原因：端口被占（`lsof -i :11459`）、venv 缺依赖（重跑 `pip install -e "fusion-code-modelization[server]"`）。
2. 报 `health check timed out after 30s` → 进程活着但 `/health` 不 200。`curl http://127.0.0.1:11459/health` 看依赖检查：`gateway` 不可达时 `/health` 明示 `unreachable`。先确认 fusion-gateway `:11432` 在线，再核对 `FUSION_GATEWAY_URL`。
3. 残留 PID 文件（进程已死但 `.fusion-code-modelization.pid` 还在）→ `start.sh start` 误判 "already running"。删 PID 文件后重启；`start.sh stop` 对死进程会自动清理。

## LLM 调用失败 / LLM call fails

1. `TimeoutError` → `FUSION_TIMEOUT` 默认 120s；大仓库 transpile/refactor 适当调大，或先用 `decompose` 拆任务。
2. 网关 5xx / 连接拒绝 → fusion-gateway 或其上游 fusion-mlx 不在线；`~/fusion/fusion-mlx/start.sh status` 与网关日志。重试次数由 `FUSION_RETRY_ATTEMPTS` 控制（默认 2）。
3. 模型不存在报错 → `FUSION_MODEL_ID` 与网关已加载模型不匹配；查 fusion-mlx `start.sh status` 的 loaded models。

## 会话与状态 / Sessions and state

1. 重启后 session 消失 → 会话状态在服务进程内，不做持久化恢复；长任务先 `distribute` 并在重启前 `merge`。
2. `merge` 结果不完整 → 检查 `/api/sessions/{id}/cluster-status`，确认所有分片完成后再 merge。
3. 请求 413 / body 被拒 → 超过 `FUSION_MAX_BODY_BYTES`（默认 1 MiB）；缩小载荷或显式调大上限。

## 鉴权 401 / Auth failures

1. 服务端鉴权 token 与网关 key 是同一密钥（`FUSION_CLIENT_KEY`）。dev 下未设 key 时为空串 + 一次性 warn（anonymous dev mode）；`FUSION_PROFILE=prod` 下缺失直接 `RuntimeError` —— 这是预期失败，设置变量后重启。
2. 使用旧名 `FUSION_MLX_API_KEY` / `MLX_API_KEY` 会在日志出现 deprecated warn —— 迁移到 `FUSION_CLIENT_KEY`。

## 快照与回滚 / Snapshots

1. 回滚后文件状态不符合预期 → 回滚覆盖工作区文件；先确认没有未保存修改。快照数据丢失问题在 0.7.x 修复过（#27-#31），保持版本 >= 0.7.5。
2. 快照是本机数据，不随 git 同步；跨机器不要依赖快照迁移。

## 测试 / Tests

1. 离线套件失败 → 默认 `pytest` 已排除 `live` 标记；先在仓库根 venv 运行，确认 fusion-core 已安装（`pip show fusion-core`）。
2. `live` 用例被跳过是正常行为；需要真实网关时显式 `python -m pytest -m live`。

## 诊断入口 / Diagnostics

- `start.sh status` / `start.sh log [-f]`
- `GET /health`（gateway/disk 依赖检查）、`GET /metrics`
- CLI 侧确认：`fusion-code-modelization version` 应输出 `0.7.5`
