# Fusion-Code-Modelization 重构计划

## 基准分析

### 当前代码状态
- 9 个子模块，其中 `decompose/` 和 `doc_gen/` 为空占位
- 所有 LLM 调用硬编码模型 `qwen3.5-9b`，无模型选择能力
- 所有模块直接用 `httpx.AsyncClient` 调用 fusion-mlx，无统一客户端抽象
- `_extract_code()` 在 4 个模块中重复实现（transpiler/refactorer/generator/scanner）
- 无会话管理、无快照系统、无工作流引擎
- 测试全量 mock HTTP 调用，无真实模型集成测试路径
- CLI 仅 argparse，无交互式命令

### 增强文档要求（coding-modenization-enhance.md）
核心增强对标 Claude Code Modernization，分三个版本阶段：

| 阶段 | 目标 | 核心能力 |
|------|------|----------|
| V1.0 基线 | 复刻 Claude Code 核心能力 | 并行会话、安全沙箱、快照回滚、项目记忆、Dynamic Workflow |
| V1.5 差异化 | 补齐竞品短板 | fusion-mlx 本地模型双栈、分布式集群调度、增量快照、企业审计 |
| V2.0 生态壁垒 | 独有能力 | 自动化测试闭环、智能负载均衡、全链路追踪、Agent 跨机通信 |

## 重构计划（V1.0 基线阶段，分 6 个 Task）

### Task 1: 统一 MLX 客户端 + 模型双栈调度
**问题**: 4 个模块各自 `httpx.AsyncClient` 调用 fusion-mlx，硬编码模型名
**目标**: 抽取 `MLXClient` 统一客户端，支持模型选择、重试、超时、流式响应

```
fusion_code_modelization/
├── core/
│   ├── __init__.py          # 导出 MLXClient
│   ├── client.py            # MLXClient: 统一 HTTP 客户端
│   └── config.py            # ModelConfig: 模型配置、调度策略
```

- `MLXClient` 封装 httpx 调用，提供 `chat()`, `chat_stream()`, `extract_code()` 方法
- `ModelConfig` 支持模型名、temperature、max_tokens 配置，后续扩展云端模型
- 所有现有模块的 LLM 调用改为 `MLXClient` 实例方法调用
- 删除 4 处重复的 `_extract_code()`

### Task 2: 会话引擎（并行多 Agent 会话）
**问题**: 无会话概念，CLI 每次调用是独立无状态操作
**目标**: 实现 `SessionEngine`，支持多会话并行、状态机、会话隔离

```
fusion_code_modelization/
├── session/
│   ├── __init__.py
│   ├── engine.py            # SessionEngine: 会话生命周期管理
│   ├── state.py             # SessionState 枚举 + 状态机
│   └── store.py             # SessionStore: 会话持久化（JSON 文件）
```

- 会话状态机: idle → running → waiting_approval → paused → completed / failed
- 每个会话独立工作目录、上下文、权限、模型实例
- `SessionStore` 持久化到 `.fusion/sessions/` 目录
- 会话克隆、快照创建、批量操作

### Task 3: 安全沙箱系统
**问题**: 无权限管控，Agent 可任意读写文件、执行命令
**目标**: 三级安全模式 + 目录边界隔离 + 操作审计

```
fusion_code_modelization/
├── sandbox/
│   ├── __init__.py
│   ├── policy.py            # SandboxPolicy: 三级策略定义
│   ├── guard.py             # SandboxGuard: 文件/命令拦截器
│   └── audit.py             # SandboxAudit: 操作审计日志（迁移自 pipeline）
```

- 三级模式: readonly / manual / auto
- `SandboxGuard` 拦截文件读写（边界检查）、命令执行（高危命令黑名单）
- `SandboxAudit` 从 `PipelineIntegrator` 迁移审计能力，增强为不可删除日志
- 解析 `.gitignore` / `.fusionignore` 自动排除文件

### Task 4: 快照与回滚系统
**问题**: 无代码变更快照，修改出错无法回退
**目标**: 增量快照 + /rewind 一键回滚

```
fusion_code_modelization/
├── snapshot/
│   ├── __init__.py
│   ├── manager.py           # SnapshotManager: 创建/恢复/列出快照
│   └── delta.py             # DeltaStore: 增量存储（基于文件 diff）
```

- 每次批量修改前自动创建快照
- `DeltaStore` 仅存储变更部分（增量），非全量拷贝
- 恢复可选: 仅代码 / 仅对话 / 全部
- 快照存储在 `.fusion/snapshots/`

### Task 5: Dynamic Workflow 动态工作流引擎
**问题**: 大型任务只能单线程串行处理
**目标**: 自动拆解任务，派生子 Agent 并行执行，结果汇聚

```
fusion_code_modelization/
├── workflow/
│   ├── __init__.py
│   ├── engine.py            # WorkflowEngine: 工作流调度核心
│   ├── task.py              # Task / SubTask: 任务模型
│   └── templates.py         # 内置工作流模板（迁移、扫描、批量改造）
```

- `WorkflowEngine` 接收大任务 → LLM 拆解为子任务 → 分配会话并行执行
- 内置模板: 遗留系统迁移、全项目漏洞扫描、批量接口改造
- 子任务完成后主 Agent 统一整合、冲突修复
- 支持自定义工作流模板

### Task 6: 项目记忆系统（FUSION.md）
**问题**: 无项目级持久记忆，每次会话丢失上下文
**目标**: 三级记忆体系 + 可视化编辑支持

```
fusion_code_modelization/
├── memory/
│   ├── __init__.py
│   ├── store.py             # MemoryStore: 三级记忆读写
│   └── init.py              # /init 扫描项目、生成 FUSION.md
```

- 三级: `~/.fusion/FUSION.md`（全局）→ `./FUSION.md`（项目）→ 子目录规则
- `/init` 自动扫描项目结构、依赖、语言分布，生成初始 FUSION.md
- 会话启动自动加载对应层级记忆
- 支持记忆增删改查 API

---

## 重构后的包结构

```
fusion_code_modelization/
├── __init__.py
├── core/                    # Task 1: 统一客户端 + 配置
│   ├── __init__.py
│   ├── client.py
│   └── config.py
├── session/                 # Task 2: 会话引擎
│   ├── __init__.py
│   ├── engine.py
│   ├── state.py
│   └── store.py
├── sandbox/                 # Task 3: 安全沙箱
│   ├── __init__.py
│   ├── policy.py
│   ├── guard.py
│   └── audit.py
├── snapshot/                # Task 4: 快照回滚
│   ├── __init__.py
│   ├── manager.py
│   └── delta.py
├── workflow/                # Task 5: 动态工作流
│   ├── __init__.py
│   ├── engine.py
│   ├── task.py
│   └── templates.py
├── memory/                  # Task 6: 项目记忆
│   ├── __init__.py
│   ├── store.py
│   └── init.py
├── analyzer/                # 保留，改造为使用 MLXClient
│   ├── __init__.py
│   └── dependency.py
├── migration/               # 保留，改造为使用 MLXClient
│   ├── __init__.py
│   └── transpiler.py
├── refactor/                # 保留，改造为使用 MLXClient
│   ├── __init__.py
│   └── refactorer.py
├── test_gen/                # 保留，改造为使用 MLXClient
│   ├── __init__.py
│   └── generator.py
├── security/                # 保留，改造为使用 MLXClient
│   ├── __init__.py
│   └── scanner.py
├── pipeline/                # 保留，审计能力迁移至 sandbox/audit.py
│   └── __init__.py
├── pr_gen/                  # 保留，改造为使用 MLXClient
│   └── __init__.py
├── decompose/               # 实现内容，迁移自 pr_gen/MicroserviceDecomposer
│   └── __init__.py
├── doc_gen/                 # 实现内容，迁移自 pr_gen/DocGenerator
│   └── __init__.py
└── cli/                     # 保留，扩展子命令
    └── __init__.py
```

## 执行顺序与依赖

```
Task 1 (core) ← 无依赖，首先实施
  ↓
Task 2 (session) ← 依赖 Task 1（MLXClient）
  ↓
Task 3 (sandbox) ← 依赖 Task 2（会话绑定沙箱策略）
Task 4 (snapshot) ← 依赖 Task 2（快照绑定会话）
  ↓
Task 5 (workflow) ← 依赖 Task 2 + 4（工作流调度会话 + 快照）
Task 6 (memory) ← 依赖 Task 1（记忆读取用 MLXClient）
  ↓
现有模块改造（全部迁移至 MLXClient）
CLI 扩展（新增 session/snapshot/workflow 子命令）
```

## 测试策略

- 每个 Task 完成后同步编写单元测试（mock HTTP）
- Task 1 完成后，新增 `tests/conftest.py` 提供 `mlx_client` fixture
- 保留现有 70 个测试全部通过
- 新增 `tests/integration/` 目录，标记 `@pytest.mark.integration`，需要真实 fusion-mlx 运行

## 风险

- Task 2 会话引擎是最复杂模块，异步并发需注意资源竞争
- Task 4 增量快照需选择合适的 diff 算法，大文件性能是关键
- Task 5 工作流拆解依赖 LLM 质量，需设计 fallback 策略
