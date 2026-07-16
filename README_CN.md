<div align="center">

# Fusion-Code-Modelization

**遗留系统代码现代化与跨语言迁移平台**

翻新、重构、迁移老旧业务代码——完全本地运行，由 fusion-mlx 驱动。

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-70-success.svg)](tests/)

[English](README.md) · [快速开始](#快速开始) · [CLI 参考](#cli-参考) · [架构](#架构) · [文档](docs/)

</div>

---

## 为什么选择 Fusion-Code-Modelization？

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
| **微服务拆分** | ✅ | ✅ |
| **Git 集成** | ✅ Gitee, GitHub, GitLab | ✅ 仅 GitHub |

**一句话：** Fusion-Code-Modelization 是 Claude Code Modernization 的本地优先、隐私合规替代方案——由 fusion-mlx 在 Apple Silicon 上驱动。

---

## 快速开始

### 前置条件

- macOS Apple Silicon (M1–M5)
- Python 3.12+
- [fusion-mlx](https://github.com/dahai80/fusion-mlx) 运行在 `localhost:11434`

### 安装

```bash
git clone https://github.com/dahai80/fusion-code-modelization.git
cd fusion-code-modelization
pip install -e ".[test]"
```

### 分析代码库

```bash
# 分析依赖并生成报告
fusion-code-modelization analyze /path/to/codebase --output=report.md

# 查看报告
cat report.md
```

### 跨语言迁移

```bash
# Python 转 Java
fusion-code-modelization transpile input.py --from=python --to=java --output=output.java

# COBOL 转 Go
fusion-code-modelization transpile legacy.cbl --from=cobol --to=go --output=modern.go
```

### 安全重构

```bash
# 测试先行重构
fusion-code-modelization refactor legacy_code.py --output=refactored.py

# 带特定指令
fusion-code-modelization refactor messy_code.py --instructions="提取辅助函数，添加类型注解"
```

### 生成测试

```bash
fusion-code-modelization test-gen source.py --output=tests.py
```

### 安全扫描

```bash
fusion-code-modelization security legacy_code.py --output=security_report.json
```

---

## CLI 参考

| 命令 | 说明 |
|------|------|
| `analyze <path> [--output]` | 分析代码库依赖并生成报告 |
| `transpile <file> --from --to [--output]` | 跨语言迁移代码 |
| `refactor <file> [--instructions] [--output]` | 增量重构代码 |
| `test-gen <file> [--language] [--output]` | 生成单元测试 |
| `security <file> [--language] [--output]` | 安全漏洞扫描 |
| `version` | 显示版本信息 |

### 支持的语言

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

```
┌─────────────────────────────────────────────────────────────────┐
│                    Fusion-Code-Modelization CLI                  │
│  analyze · transpile · refactor · test-gen · security           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                     核心引擎                                     │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ 依赖分析器     │  │ 代码迁移器     │  │ 增量重构器       │  │
│  │ (死代码/技术债) │  │ (COBOL→Java等) │  │ (测试先行/双校验) │  │
│  └────────────────┘  └────────────────┘  └──────────────────┘  │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ 测试生成器     │  │ 安全扫描器     │  │ 流水线集成器     │  │
│  │ (单元/集成测试)│  │ (密钥/注入漏洞) │  │ (Git/CI-CD/PR)   │  │
│  └────────────────┘  └────────────────┘  └──────────────────┘  │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ PR生成器       │  │ 文档生成器     │  │ 微服务拆分器     │  │
│  └────────────────┘  └────────────────┘  └──────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP API (所有模型调用)
┌───────────────────────────▼─────────────────────────────────────┐
│                    fusion-mlx (/v1/chat/completions)              │
│                    Apple Silicon MLX Runtime                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 与 Claude Code Modernization 对比

| 能力 | Claude Code | Fusion-Code-Modelization |
|------|-------------|--------------------------|
| 代码依赖分析 | ✅ | ✅ |
| 死代码检测 | ✅ | ✅ |
| 技术债估算 | ✅ | ✅ |
| 跨语言迁移 | ✅ COBOL→Java | ✅ COBOL→Java, VB6→C# |
| 测试先行重构 | ✅ | ✅ |
| 双跑校验 | ✅ | ✅ |
| 单元测试生成 | ✅ | ✅ |
| 安全漏洞扫描 | ✅ | ✅ |
| 企业流水线 | ✅ | ✅ |
| 迁移优先级评分 | ✅ | ✅ |
| 微服务拆分 | ✅ | ✅ |
| 审计日志 | ✅ | ✅ |
| **本地离线** | ❌ 仅云端 | ✅ **100% 本地** |
| **数据隐私** | ❌ 代码上传海外 | ✅ **数据不出设备** |
| **国内合规** | ❌ 违反数据安全法 | ✅ **完全合规** |
| **零费用** | ❌ 企业订阅 | ✅ **免费** |
| **Gitee/GitLab** | ❌ 仅 GitHub | ✅ **全平台** |

---

## 开发

```bash
# 安装开发依赖
pip install -e ".[test]"

# 运行测试
pytest tests/

# 带覆盖率运行
pytest tests/ --cov=fusion_code_modelization
```

### 测试统计
- **70 个测试**, 0 失败
- **96%+** 语句覆盖率
- **Python 3.12+** 兼容

---

## 许可证

MIT

## 致谢

- [fusion-mlx](https://github.com/dahai80/fusion-mlx) — Apple Silicon 模型服务
- [Claude Code Modernization](https://docs.anthropic.com/en/docs/claude-code) — 参考架构