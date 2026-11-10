---
doc_id: fusion-code-modelization/recon
product: fusion-code-modelization
class: app
entry: service
doc_type: guide
title: {zh: "REA 证据级侦察集成", en: "REA Evidence-Grade Recon Integration"}
audience: engineer
status: draft
version: 0.8.0
updated: 2026-11-10
owner: "@dahai"
source_of_truth:
  - fusion_code_modelization/recon/engine.py
  - fusion_code_modelization/recon/mcp_client.py
  - fusion_code_modelization/recon/parity.py
---

# REA 证据级侦察集成 / REA Evidence-Grade Recon Integration

`fusion-code-modelization recon` 挂载外部 REA MCP 服务器（`npx rea-agents`，MIT），对**客户拥有或已获书面授权**的遗留目标做证据级侦察（issue #37）。REA 每条 finding 附带证据，产物为版本化、可审计的 pipeline artifact。仅运行在 operator 基础设施上；目标需第三方授权的场景不在本功能范围内。

## 机制

- 传输：stdio JSON-RPC 子进程（与 fusion-cowork desigma 集成同型，本仓自持实现）。
- 白名单：`FUSION_FCM_MCP_STDIO_ALLOW`（逗号/分号分隔的二进制 basename，精确匹配）。**空/未设置 = 一律拒绝（fail-closed）** — 引擎不可能隐式 spawn 未授权进程。
- 降级：任何 MCP 失败（白名单拒绝、spawn 失败、协议错误、超时）→ `status="skipped"`，管线无侦察继续。`/health` 与 CI 不受影响，离线约束保持。

## 用法

```bash
export FUSION_FCM_MCP_STDIO_ALLOW=npx
fusion-code-modelization recon --target /path/to/legacy-binary
# 连带 parity loop（modernized vs legacy 运行时探针证据比对；--parity-query 提供探针 query）：
fusion-code-modelization recon --target /path/to/legacy-binary --parity-modernized /path/to/modernized --parity-query "export report"
```

参数：`--data-dir`（产物目录，默认 `~/.fusion/code_mod`）、`--mcp-command`（默认 `npx`）、`--mcp-args`（默认 `-y rea-agents mcp`）、`--timeout`（单请求超时，默认 120s）、`--parity-query`（parity 探针 feature query；未提供时 parity 跳过——探针参数是业务语义，引擎不猜测）。

## 产物

- `recon/<run_id>/manifest.json`（`artifact_version: 1`）：target、命令、白名单快照、工具计划、逐工具 findings + 证据全文、注入 coder prompt 用的 `context_section`。
- `recon/<report_id>/manifest.json`（parity 报告）：`verdict`（match/divergence）、逐探针 legacy/modernized 证据对照。parity 结论必须引用探针证据，不接受纯 source diff（issue #37 验收）。

## 默认工具计划

引擎在计划前自动注入 `open_binary`（挂载 target，参数为绝对路径）。默认计划：`inspect_macho` → `batch_decompile` → `export_evidence_bundle`（证据包落盘到 `recon/<run_id>/evidence-bundle.json`；工具名对照 rea-agents 6.7.0 `tools/list`，207 个工具）。计划内工具无需预先配置反编译 provider；`binary_overview`/`list_strings` 等需要 Ghidra/Hopper/IDA/Kuna，未配置时返回 provider_unavailable 错误证据（照样记录，不中断）。调用方可用 `ReconEngine.run(target, plan=...)` 覆盖。

## 故障排查

| 症状 | 原因 | 处理 |
|---|---|---|
| `Recon skipped: ... not in FUSION_FCM_MCP_STDIO_ALLOW allowlist` | 白名单空或缺 `npx` | `export FUSION_FCM_MCP_STDIO_ALLOW=npx` |
| `Recon skipped: ... timed out after Ns` | 首次 `npx -y rea-agents` 下载超时 | 预热 `npx -y rea-agents --version` 后重试 |
| `Recon skipped: ... failed to spawn` | node/npx 不在 PATH | 安装 Node.js ≥ 20 |
