<div align="center">

# Fusion-Code-Modelization

**遗留系统代码现代化与跨语言迁移平台**

翻新、重构、迁移老旧业务代码——完全本地运行，经 fusion-gateway 路由、由 fusion-mlx 驱动。

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-727+-success.svg)](tests/)

[English](README.md) · [快速开始](#快速开始) · [CLI 参考](#cli-参考) · [架构](#架构) · [更新日志](#更新日志)

</div>

---

## 为什么选择 Fusion-Code-Modelization？

<!-- feature-table -->
| 特性 | Fusion-Code-Modelization | Claude Code Modernization |
|------|--------------------------|--------------------------|
| **本地离线** | ✅ 100% 本地 | ❌ 仅云端 |
| **数据隐私** | ✅ 数据不出设备 | ❌ 代码上传海外 |
| **国内合规** | ✅ 完全合规 | ❌ 违反《数据安全法》 |
| **零 API 费用** | ✅ | ❌ 企业订阅付费 |
| **跨语言迁移** | ✅ COBOL→Java, VB6→C# 等 | ✅ |
| **安全增量重构** | ✅ 测试先行 + 双跑校验 | ✅ |
| **安全扫描** | ✅ 静态规则 + LLM 分析 | ✅ |
| **企业流水线** | ✅ Git/CI-CD/PR/审计日志 | ✅ |
| **流式 LLM 输出** | ✅ 实时 token 流式 | ❌ |
| **进度回调** | ✅ 可组合回调系统 | ❌ |
| **微服务拆分** | ✅ | ✅ |
| **Git 集成** | ✅ Gitee, GitHub, GitLab | ✅ 仅 GitHub |
| **并行多 Agent 会话** | ✅ SessionEngine | ✅ |
| **动态工作流** | ✅ LLM 任务拆解 | ✅ |
| **增量快照** | ✅ FileDelta + SnapshotManager | ✅ |
| **三层项目记忆** | ✅ FUSION.md（全局/项目/目录） | ✅ CLAUDE.md |
| **安全沙箱** | ✅ 三层（只读/手动/自动） | ✅ |
| **双栈模型路由** | ✅ 本地/云端 + 复杂度路由 | ✅ |
| **企业审计** | ✅ JSONL + 搜索/导出/统计 | ✅ |
| **集群调度** | ✅ 节点注册 + 自动调度 | ✅ |
| **MCP 插件平台** | ✅ 注册表 + 生命周期管理 | ✅ |
| **基准测试套件** | ✅ 代码质量/性能/迁移/安全 | ✅ |
| **集群负载均衡** | ✅ 4 策略（轮询/最少负载/加权/亲和） | ✅ |
| **离线部署** | ✅ 全离线/半离线/在线 + 能力矩阵 | ✅ |
| **全链路可追溯** | ✅ 制品追踪 + 前向/后向 BFS 遍历 | ✅ |
| **Agent 跨机通信** | ✅ 基于通道的协作 + 冲突解决 | ✅ |

---

## 快速开始

### 前置条件

<!-- prerequisites -->
- macOS Apple Silicon (M1–M5)
- Python 3.12+
- [fusion-gateway](https://github.com/dahai80/fusion-gateway) 运行在 `localhost:11432`（统一推理网关），其上游 [fusion-mlx](https://github.com/dahai80/fusion-mlx) 运行在 `localhost:11434`

### 认证与模型 ID

<!-- auth-model -->
所有推理经 **fusion-gateway**（`localhost:11432/v1`）路由；本包**不**直连 fusion-mlx（`localhost:11434`）。`MLXClient` 用 bearer token 向网关认证。API key 按优先级解析（首个非空胜出）：

1. `FUSION_MLX_API_KEY` 环境变量 —— **网关客户端密钥**（如 `fg-admin-key`）
2. `MLX_API_KEY` 环境变量
3. `OPENAI_API_KEY` 环境变量

> ⚠️ 该密钥必须是 fusion-gateway `config.yaml`（`auth.api_keys`）中注册的网关客户端密钥，**不是** fusion-mlx 上游密钥。未设置则以无认证方式请求，网关会拒绝。

默认本地模型 id 为 `Qwen3.5-9B-4bit`（须与网关 fusion-mlx 上游加载的模型一致 —— 用 `~/claude-home/fusion-mlx/start.sh status` 查看）。按调用覆盖：`MLXClient(...).chat(model=...)`，或构造自定义 `ModelConfig`。

```bash
export FUSION_MLX_API_KEY="<网关客户端密钥>"   # 如 fg-admin-key
```

### 安装

<!-- install -->
```bash
git clone https://github.com/dahai80/fusion-code-modelization.git
cd fusion-code-modelization
pip install -e ".[test]"
```

### 分析代码库

<!-- analyze -->
```bash
fusion-code-modelization analyze /path/to/codebase --output=report.md
```

### 跨语言迁移

<!-- transpile -->
```bash
# Python 转 Java
fusion-code-modelization transpile input.py --from=python --to=java --output=output.java

# COBOL 转 Go（实时流式）
fusion-code-modelization transpile legacy.cbl --from=cobol --to=go --stream

# COBOL 转 Go + Agent Loop 自愈（校验逻辑等价性，失败自动重试）
fusion-code-modelization transpile legacy.cbl --from=cobol --to=go --loop --max-iter=5
```

### 安全重构

<!-- refactor -->
```bash
fusion-code-modelization refactor legacy_code.py --instructions="添加类型注解" --output=refactored.py

# Agent Loop 自愈（双运行等价校验 + 自动重试）
fusion-code-modelization refactor legacy_code.py --instructions="添加类型注解" --loop --output=refactored.py
```

### 生成测试

<!-- test-gen -->
```bash
fusion-code-modelization test-gen source.py --output=tests.py
```

### 安全扫描

<!-- security -->
```bash
fusion-code-modelization security legacy_code.py --output=security_report.json
```

### 生成文档

<!-- doc-gen -->
```bash
# 模块文档
fusion-code-modelization doc-gen source.py --type=module --output=docs.md

# API 文档（流式）
fusion-code-modelization doc-gen api.py --type=api --stream
```

---

## CLI 参考

<!-- cli-table -->
| 命令 | 说明 |
|------|------|
| `analyze <path> [--output]` | 分析代码库依赖并生成报告 |
| `transpile <file> --from --to [--output] [--stream]` | 跨语言迁移代码 |
| `refactor <file> [--instructions] [--output] [--stream]` | 增量重构代码 |
| `test-gen <file> [--language] [--output] [--stream]` | 生成单元测试 |
| `security <file> [--language] [--output] [--stream]` | 安全漏洞扫描 |
| `doc-gen <file> [--type] [--language] [--output] [--stream]` | 文档生成（模块/类/API） |
| `session <action> [--id] [--name]` | 并行会话管理（create/list/start/pause/resume/complete/delete） |
| `snapshot <action> [--project-dir] [--id] [--label] [--steps]` | 增量快照与回滚（create/list/restore/rewind/delete） |
| `workflow <action> [--description] [--template] [--max-parallel]` | 动态任务拆解与执行（decompose/run） |
| `memory <action> [--project-dir] [--query]` | 三层项目记忆（init/list/load/query） |
| `sandbox <action> [--path] [--mode]` | 安全沙箱与审计（check/audit） |
| `decompose <path> [--method] [--output]` | 微服务边界检测（static/llm） |
| `audit <action> [--actor] [--severity]` | 企业审计日志（log/search/export/stats/cleanup） |
| `cluster <action> [--node-id] [--session-id]` | 分布式集群调度（discover/dispatch/status/schedule/migrate/register/tasks） |
| `plugin <action> [--plugin-id] [--query]` | MCP 插件平台（list/search/install/load/unload/execute/status） |
| `benchmark <action> [--suite] [--report-id]` | 运行基准套件并对比报告（run/list/compare/history） |
| `loadbalancer <action> [--strategy]` | 集群负载均衡（overview/rebalance/predict/select） |
| `offline <action> [--mode] [--package-dir]` | 离线部署管理（detect/capabilities/prepare/validate/restore） |
| `trace <action> [--artifact-type] [--artifact-id]` | 端到端可追溯（create/link/forward/backward/report） |
| `agent-comm <action> [--agents] [--collab-id]` | Agent 跨机通信（create/submit/conflict/resolve/complete/list/status） |
| `version` | 显示版本信息 |
| `serve [--host] [--port] [--mlx-url]` | 启动 REST API 服务器（默认 `127.0.0.1:11459`） |
| `--json` | 全局标志：以 JSON 输出结果 |
| `--verbose` / `-v` | 全局标志：开启调试日志 |
| `--quiet` / `-q` | 全局标志：抑制非错误输出 |

### 流式模式

<!-- streaming -->
调用 LLM 的命令支持 `--stream` 实时 token 输出：

```bash
fusion-code-modelization transpile src.py --from=python --to=java --stream
fusion-code-modelization refactor src.py --stream
fusion-code-modelization test-gen src.py --stream
fusion-code-modelization security src.py --stream
fusion-code-modelization doc-gen src.py --stream
```

### Agent Loop 自愈引擎

<!-- agent-loop -->
`--loop` 为 `transpile`、`refactor`、`test-gen` 启用**有界、全量追踪**的自愈循环。模型只决定
**如何修复**未通过校验的输出，**不**选择运行哪个工具——工具序列固定，保证确定性与可审计。
每次迭代：构造 prompt → LLM → 提取代码 → 校验工具 → 失败则将错误反馈并重试，上限
`--max-iter`（默认 5）。每次运行写一份 JSONL 追踪。

```bash
# transpile + 逻辑等价性校验
fusion-code-modelization transpile legacy.cbl --from=cobol --to=go --loop --max-iter=5

# refactor + 双运行等价校验
fusion-code-modelization refactor legacy_code.py --loop

# test-gen + 语法校验（Python 用 compile()，其它语言用 LLM 校验）
fusion-code-modelization test-gen legacy_code.py --loop
```

| 标志 | 适用 | 说明 |
|------|------|------|
| `--loop` | transpile / refactor / test-gen | 启用 Agent Loop 自愈（优先级高于 `--stream`） |
| `--max-iter N` | transpile / refactor / test-gen | 最大迭代次数（默认 5） |

### Hook 拦截层

<!-- hooks -->
模型**无法绕过**的确定性拦截层。Hook 注册表让内置拦截器可 `allow` / `deny` / `modify` 负载。
覆盖范围按**事件划分**，非全覆盖：

| 事件 | 发射位置 | 范围 |
|------|----------|------|
| `PRE_WRITE` | `SafeWriter`（所有包内写点：snapshot / session / audit / CLI 输出） | 经统一 writer 的每次写入 |
| `POST_LLM` | `AgentLoop`（仅 `--loop` 路径：transpile / refactor / test-gen） | 仅自愈循环 |
| `PRE_EXEC` | `AgentLoop` verify 工具执行 + `PipelineIntegrator` shell | 循环工具执行 + pipeline git/subprocess |
| `POST_EXEC` | `PipelineIntegrator` shell | pipeline git/subprocess |

**非循环 LLM 调用**（普通 `transpile` / `refactor` / `scan` / `doc-gen` / `session` / `workflow`）
**不**发射 `POST_LLM` —— 它们直接调用 `MLXClient.chat()`，绕过注册表。要让某 LLM 路径获得 hook
覆盖，使用 `--loop`。

内置拦截器：
- `path_guard`（`PRE_WRITE`）—— 阻止路径穿越 / 系统目录。
- `dangerous_cmd_guard`（`PRE_EXEC`）—— 阻止破坏性 shell 命令（`rm -rf /`、fork 炸弹、`mkfs` 等），fail-closed 白名单。
- `secret_scrub`（`POST_LLM`）—— 脱敏 LLM 输出中泄露的密钥（AWS key、`sk-*`、`ghp_*`、私钥）。
- `audit_log`（`POST_EXEC`）—— 记录执行的 pipeline 动作。
- `guard_evaluate`（`POST_LLM` + `PRE_WRITE`）—— 有融合守卫时委托 `fusion-core.guard_client` →
  fusion-guard（UDS JSON-RPC），守卫不可用时回退正则 + `WARNING` 日志。

```bash
# --loop 时默认开启；用全局标志关闭：
fusion-code-modelization --no-hooks transpile src.py --from=python --to=go --loop
```

### REST API 服务器

<!-- rest-api -->
Issue #3 —— FastAPI 服务器，经 HTTP/WebSocket 暴露会话、工作流与集群操作：

```bash
# 安装服务器可选依赖（fastapi + uvicorn）
pip install -e ".[server]"

# 启动服务器（默认 127.0.0.1:11459）
fusion-code-modelization serve --port 11459

# 或通过模块
python -m fusion_code_modelization.server.runner
```

| 方法 | 端点 | 用途 |
|------|------|------|
| `GET` | `/health` | 健康检查 |
| `GET` / `POST` | `/api/sessions` | 列出 / 创建会话 |
| `GET` | `/api/sessions/{id}` | 获取会话快照 |
| `POST` | `/api/sessions/{id}/{action}` | start / pause / resume / complete / fail / delete / clone |
| `POST` | `/api/sessions/{id}/chat` | 发送聊天消息 |
| `POST` | `/api/sessions/{id}/distribute` | 分发会话到集群节点（Issue #4） |
| `GET` | `/api/sessions/{id}/cluster-status` | 查询集群分发状态 |
| `POST` | `/api/sessions/{id}/merge` | 合并完成的集群结果 |
| `POST` | `/api/workflows/run` | 拆解 + 执行工作流 |
| `GET` | `/api/workflows/{plan_id}` | 获取已存工作流结果 |
| `WS` | `/ws/chat` | 经 WebSocket 流式聊天 |

交互式 API 文档自动提供于 `/docs`（Swagger）与 `/redoc`。

### 支持的语言

<!-- languages -->
| 语言 | 分析 | 迁移 | 测试生成 | 安全扫描 |
|------|------|------|---------|---------|
| Python | ✅ | ✅ | ✅ | ✅ |
| Java | ✅ | ✅ | ✅ | ✅ |
| Go | ✅ | ✅ | ❌ | ✅ |
| JavaScript/TypeScript | ✅ | ✅ | ❌ | ✅ |
| C/C++ | ✅ | ❌ | ❌ | ✅ |
| C# | ✅ | ✅ | ❌ | ✅ |
| COBOL | ✅ | ✅ | ❌ | ❌ |
| VB6 | ✅ | ✅ | ❌ | ❌ |
| Ruby | ✅ | ❌ | ❌ | ❌ |
| Swift | ✅ | ❌ | ❌ | ❌ |
| Rust | ✅ | ❌ | ❌ | ❌ |
| PHP | ✅ | ❌ | ❌ | ❌ |

---

## 架构

<!-- architecture -->
```
┌─────────────────────────────────────────────────────────────────┐
│                    Fusion-Code-Modelization CLI                  │
│  analyze · transpile · refactor · test-gen · security · session  │
│  snapshot · workflow · memory · sandbox · decompose · doc-gen    │
│  audit · cluster · plugin · benchmark · loadbalancer · offline   │
│  trace · agent-comm                                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                     核心引擎                                     │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ 依赖分析器     │  │ 代码迁移器     │  │ 增量重构器       │  │
│  │ (死代码/技术债) │  │ (COBOL→Java等) │  │ (测试先行/双校验) │  │
│  │ + 流式         │  │ + 流式         │  │ + 流式           │  │
│  └────────────────┘  └────────────────┘  └──────────────────┘  │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ 测试生成器     │  │ 安全扫描器     │  │ 流水线集成器     │  │
│  │ (单元/集成测试)│  │ (密钥/注入漏洞) │  │ (Git/CI-CD/PR)   │  │
│  │ + 流式         │  │ + 流式         │  └──────────────────┘  │
│  └────────────────┘  └────────────────┘                        │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ PR 生成器      │  │ 文档生成器     │  │ 微服务拆分器     │  │
│  │ (PR 描述/变更) │  │ (迁移报告/API) │  │ (边界分析)       │  │
│  └────────────────┘  └────────────────┘  └──────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP API (所有模型调用)
┌───────────────────────────▼─────────────────────────────────────┐
│              fusion-gateway → fusion-mlx (/v1/chat/completions)   │
│              Apple Silicon MLX Runtime                           │
└─────────────────────────────────────────────────────────────────┘
```

### 核心模块

<!-- key-modules -->
| 模块 | 文件 | 说明 |
|------|------|------|
| **依赖分析器** | `analyzer/dependency.py` | 代码依赖图、死代码检测、技术债估算 |
| **代码迁移器** | `migration/transpiler.py` | 跨语言迁移 + 流式（`transpile_stream()`） |
| **增量重构器** | `refactor/refactorer.py` | 测试先行重构 + 双跑校验 + 流式 |
| **测试生成器** | `test_gen/generator.py` | 单元/集成测试生成 + 流式 |
| **安全扫描器** | `security/scanner.py` | 多模式扫描：静态/静态+LLM/静态+fusion-security + 流式 |
| **文档生成器** | `doc_gen/generator.py` | 模块/类/API 文档生成 + 流式 |
| **进度回调** | `core/progress.py` | ProgressEvent、LoggingProgressCallback、CompositeProgressCallback |
| **流水线集成器** | `pipeline/integrator.py` | Git/CI-CD 集成、PR 创建、审计日志 |
| **PR 生成器** | `pr_gen/pr_generator.py` | PR 描述与变更日志生成 |
| **微服务拆分器** | `pr_gen/decomposer.py` | 单体边界分析（多粒度） |
| **MLXClient** | `core/client.py` | 统一 HTTP 客户端、代码提取、流式 |
| **ModelConfig** | `core/config.py` | 模型配置 + 预设 + 双栈路由 |
| **会话引擎** | `session/engine.py` | 并行多 Agent 会话 + 状态机生命周期 |
| **快照管理器** | `snapshot/manager.py` | 增量文件快照 + create/restore/rewind |
| **安全沙箱** | `sandbox/guard.py` | 三层（只读/手动/自动）文件与命令守卫 |
| **任务拆解器** | `workflow/decomposer.py` | LLM 驱动任务拆解 + 依赖解析 |
| **工作流执行器** | `workflow/executor.py` | 并行子 Agent 执行 + 进度回调 |
| **记忆分层管理** | `memory/tier.py` | 三层 FUSION.md（全局/项目/目录） |
| **边界检测器** | `decompose/detector.py` | 耦合分析 + LLM 微服务边界检测 |
| **审计日志器** | `audit/logger.py` | 企业审计：log/search/export（JSON/CSV/Markdown）/统计 |
| **集群调度器** | `cluster/scheduler.py` | 节点注册、任务分发、按负载自动调度 |
| **插件管理器** | `plugin/manager.py` | 插件生命周期：load/unload/execute + 动作校验 |
| **基准运行器** | `benchmark/runner.py` | 基准套件执行、报告生成、趋势对比 |
| **负载均衡器** | `loadbalancer/balancer.py` | 4 策略集群负载均衡 + 容量预测 |
| **离线管理器** | `offline/manager.py` | 离线模式检测、打包 prepare/validate/restore |
| **追踪器** | `trace/tracker.py` | BFS 前向/后向制品追踪、覆盖率报告 |
| **协作协调器** | `agent_comm/coordinator.py` | 多 Agent 协作 + 冲突检测/解决 |

---

## 开发

<!-- development -->
```bash
# 安装开发依赖
pip install -e ".[test]"

# 运行全部测试
pytest tests/

# 带覆盖率运行
pytest tests/ --cov=fusion_code_modelization

# Lint
ruff check .
ruff format --check .
```

### 测试统计

<!-- test-stats -->
- **727+ 测试**, 0 失败
- **集成测试**覆盖跨模块工作流
- **流式测试**覆盖全部 5 个 LLM 模块
- **Python 3.12+** 兼容

---

## 更新日志

<!-- changelog -->
### v0.7.1 — 企业级生产就绪审计修复 (P0-P3)
- **修复 77 条审计发现**（9 CRITICAL / 24 HIGH / 25 MEDIUM / 19 LOW），覆盖架构、安全、性能、企业就绪度、运维五个维度
- **安全**：Hook 层加固为 fail-closed（未知动作 → DENY）；快照/扫描阻断符号链接穿越；WebSocket + REST body 大小上限；CORS/Host 校验；密钥脱敏正则扩展；非 loopback 节点 http 标记；LLM 返回 JSON 在 CLI/API 返回前做 schema 校验
- **正确性**：`MemoryContext.summarize/query` 按 `chat()` 契约返回 `str`（原返回原始 dict）；流式路径补空内容 guard（issue #14 延伸）；agent loop 未知工具 fail-fast；重试补 total_deadline 上限
- **性能**：快照扫描加大小上限 + ignore 列表（build/dist/target）；死代码检测加缓存；调度器状态增量保存
- **类型安全**：mypy 18 → 0 错误；bandit CI 真门禁（去掉 `|| true`）；ruff 干净
- **运维**：`__version__` 经 importlib.metadata 单源；CLI 日志加时间戳 + logger 名；live-gateway 探活测试（`@pytest.mark.live`，默认跳过）；README_CN 与 README.md 1:1 同步；新增 `.[server]` 安装 CI job
- **版本**：0.7.0 → 0.7.1

### v0.6.5 — 服务器端口修复 (closes #16)
- **Issue #16**：REST API 服务器默认端口从 `11441` 迁至 **`11459`**，解决与 `fusion-code` 的端口冲突（按 monorepo 端口注册表 `fusion-code` 占用 `11441`）；`11459` 来自跨 40 仓库验证空闲的端口池
- **集中化**：新增 `DEFAULT_SERVER_PORT = 11459` 常量于 `core/config.py`；`server/runner.py:run_server` 与 `serve` CLI 子命令均引用之（单一来源）
- **文档**：README serve 表 + REST API 章节更新为 `11459`
- 727 测试通过，lint + format 干净

### v0.6.4 — 网关路由（不直连 fusion-mlx）
- **强制网关路由**：所有推理经 **fusion-gateway**（`localhost:11432/v1`）；本包不再直连 fusion-mlx（`localhost:11434`）
- **新默认值**：`ModelConfig.base_url` → `http://localhost:11432/v1`（`DEFAULT_GATEWAY_URL`）；集群节点端口 + 离线健康检查 → `11432`（`GATEWAY_PORT`）；CLI `--mlx-url` 与 `serve`/`cluster` 默认值对齐
- **仅环境变量密钥解析**：`_resolve_api_key()` 仅从环境变量解析 `FUSION_MLX_API_KEY` / `MLX_API_KEY` / `OPENAI_API_KEY`（移除 `~/.fusion-mlx/settings.json` 回退）；密钥须为**网关客户端密钥**（如 `fg-admin-key`），非 fusion-mlx 上游密钥
- **触及 16 个源文件**（core + 14 特性模块 + cli + server + offline + cluster），使每个 `mlx_url` 默认指向网关；`NodeClient` 发送认证头
- **经网关的真实模型验收**：chat、chat_stream、transpile、refactor、test-gen、security scan、doc-gen —— 每个 HTTP 调用均至 `localhost:11432/v1`，无 11434
- 727 测试通过，lint + format 干净

### v0.6.3 — 生产集成修复（认证 + 模型 id）
- **认证头**：`MLXClient.chat()` / `chat_stream()` 现向 fusion-mlx 发送 `Authorization: Bearer <api_key>` —— 此前无认证头，在安全实例上会被 401 拒绝
- **模型 id 对齐**：默认 `ModelConfig.model` 从 `qwen3.5-9b` 修正为 `Qwen3.5-9B-4bit`（实际加载的模型 id）；`MODEL_PRESETS`、`SessionConfig`、`SessionEngine.create_session`、`NodeClient`、`OfflineConfig` 默认值经共享 `DEFAULT_LOCAL_MODEL` 常量一致更新
- **API 密钥解析**：新增 `_resolve_api_key()` 从 `FUSION_MLX_API_KEY` / `MLX_API_KEY` / `OPENAI_API_KEY` 环境变量解析，回退至 `~/.fusion-mlx/settings.json` 的 `auth.api_key`；源码中无硬编码密钥
- **真实模型验收**：chat、chat_stream、transpile、refactor、test-gen、security scan（static+llm）、doc-gen、session chat、PR/report/decomposer 生成、集群分发、REST 服务器、CLI 均端到端确认
- 727 测试通过，覆盖率 83%，lint + format 干净

### v0.6.2 — 项目命名对齐
- **Issue #6**：`pyproject.toml` `[project] name` 对齐为 `fusion-code-modelization`，与 GitHub 仓库、CLI 入口点、可导入包（`fusion_code_modelization/`）一致；移除过时的 `fusion-code-modernization` dist 注册
- 727 测试通过，lint + format 干净

### v0.6.1 — REST API + 多节点集群会话
- **Issue #3 — REST API 服务器**：新增 `server/` 模块（FastAPI + uvicorn），暴露会话 CRUD/动作、chat（HTTP + WebSocket）、工作流 run/status、集群操作；`serve` CLI 子命令；`[server]` 可选依赖
- **Issue #4 — 多节点集群会话**：`CLUSTER_RUNNING` 会话状态 + 转换、`cluster_nodes` 配置字段（持久化）、`SessionEngine` 的 `distribute_session()` / `cluster_status()` / `merge_cluster_results()`
- **Bugfix**：CLI `session` 命令用了不存在的 `session.id`（现 `session.session_id`）
- **727 测试通过**，覆盖率 83%，lint + format 干净

### v0.6.0 — 运行时成熟度 + 流式 UX
- **流式 LLM 支持**：`transpile_stream()`、`refactor_stream()`、`generate_unit_tests_stream()`、`scan_stream()`、`generate_docs_stream()` —— 经 SSE 实时 token 输出
- **CLI `--stream` 标志**：加于 transpile、refactor、test-gen、security、doc-gen 子命令
- **进度回调系统**：`ProgressEvent`、`LoggingProgressCallback`、`CompositeProgressCallback` + 可组合 emit 辅助
- **进度接入**：session/engine、workflow/executor、decompose/detector
- **SecurityScanner 修复**：`_check_hardcoded_secrets` 正则修正；`static_only` 向后兼容默认
- **704 测试通过**，lint 干净

### v0.5.0 — 架构合规与模块拆分
- 全模块架构合规修复
- `__init__.py` 巨石拆为规范模块文件
- 8 个未覆盖模块的专属测试文件
- 跨模块集成测试
- CLI 加固与 CI 增强
- 674 测试通过

### v0.3.0 — 企业平台
- 企业审计系统（JSONL + 搜索/导出/统计）
- 集群调度（节点发现 + 自动调度）
- MCP 插件平台（注册表 + 生命周期）
- 快照优化（压缩/校验/自动清理）
- 所有新模块的 CLI 扩展

### v0.2.0 — 平台扩展
- 6 个新模块：benchmark、loadbalancer、offline、trace、agent_comm、双栈路由
- 所有新模块的 CLI 子命令
- Ruff lint + GitHub Actions CI

### v0.1.0 — 初始版本
- 核心引擎：依赖分析、迁移器、重构器、测试生成器、安全扫描器
- 流水线集成器、PR 生成器、文档生成器、微服务拆分器
- 会话引擎、快照管理器、沙箱守卫
- 动态工作流、项目记忆、边界检测器

---

## 许可证

[Apache License 2.0](LICENSE)

## 致谢

- [fusion-mlx](https://github.com/dahai80/fusion-mlx) — Apple Silicon 模型服务
- [Claude Code Modernization](https://docs.anthropic.com/en/docs/claude-code) — 参考架构
