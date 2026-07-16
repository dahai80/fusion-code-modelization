<div align="center">

# Fusion-Code-Modelization

**Legacy Code Modernization & Cross-Language Migration Platform**

Modernize, refactor, and migrate legacy codebases — entirely local, powered by fusion-mlx.

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-70-success.svg)](tests/)

[Quick Start](#quick-start) · [CLI Reference](#cli-reference) · [Architecture](#architecture) · [Documentation](docs/)

</div>

---

## Why Fusion-Code-Modelization?

| Feature | Fusion-Code-Modelization | Claude Code Modernization |
|---------|--------------------------|--------------------------|
| **Local offline** | ✅ 100% local | ❌ Cloud-only |
| **Data privacy** | ✅ Data never leaves device | ❌ Code uploaded to cloud |
| **China compliance** | ✅ Full compliance | ❌ Violates data security law |
| **Zero API cost** | ✅ | ❌ Enterprise subscription |
| **Cross-language migration** | ✅ COBOL→Java, VB6→C#, etc. | ✅ |
| **Safe incremental refactoring** | ✅ Test-first + dual-run verify | ✅ |
| **Security scanning** | ✅ Static + LLM-powered | ✅ |
| **Enterprise pipeline** | ✅ Git/CI-CD/PR/Audit logs | ✅ |
| **Microservice decomposition** | ✅ | ✅ |
| **Git integration** | ✅ Gitee, GitHub, GitLab | ✅ GitHub only |

**One sentence:** Fusion-Code-Modelization is the local-first, privacy-compliant alternative to Claude Code Modernization — powered by fusion-mlx on Apple Silicon.

---

## Quick Start

### Prerequisites

- macOS with Apple Silicon (M1–M5)
- Python 3.12+
- [fusion-mlx](https://github.com/dahai80/fusion-mlx) running on `localhost:11434`

### Install

```bash
git clone https://github.com/dahai80/fusion-code-modelization.git
cd fusion-code-modelization
pip install -e ".[test]"
```

### Analyze a Codebase

```bash
# Analyze dependencies and generate report
fusion-code-modelization analyze /path/to/codebase --output=report.md

# View report
cat report.md
```

### Transpile Code Between Languages

```bash
# Convert Python to Java
fusion-code-modelization transpile input.py --from=python --to=java --output=output.java

# Convert COBOL to Go
fusion-code-modelization transpile legacy.cbl --from=cobol --to=go --output=modern.go
```

### Refactor Code Safely

```bash
# Refactor with test-first approach
fusion-code-modelization refactor legacy_code.py --output=refactored.py

# With specific instructions
fusion-code-modelization refactor messy_code.py --instructions="Extract helper functions, add type hints"
```

### Generate Tests

```bash
fusion-code-modelization test-gen source.py --output=tests.py
```

### Security Scan

```bash
fusion-code-modelization security legacy_code.py --output=security_report.json
```

---

## CLI Reference

| Command | Description |
|---------|-------------|
| `analyze <path> [--output]` | Analyze codebase dependencies and generate report |
| `transpile <file> --from --to [--output]` | Transpile code between languages |
| `refactor <file> [--instructions] [--output]` | Refactor code incrementally |
| `test-gen <file> [--language] [--output]` | Generate unit tests |
| `security <file> [--language] [--output]` | Scan for security vulnerabilities |
| `version` | Show version info |

### Supported Languages

| Language | Analysis | Transpile | Test Gen | Security |
|----------|----------|-----------|----------|----------|
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

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Fusion-Code-Modelization CLI                  │
│  analyze · transpile · refactor · test-gen · security           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                     Core Engine                                  │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ DependencyAnaly│  │ CodeTranspiler │  │ Incremental      │  │
│  │ zer            │  │ (COBOL→Java,   │  │ Refactorer       │  │
│  │ (dead code,    │  │  VB6→C#, etc.) │  │ (test-first,     │  │
│  │  tech debt)    │  └────────────────┘  │  dual-run verify) │  │
│  └────────────────┘                      └──────────────────┘  │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ TestGenerator  │  │ SecurityScanner│  │ PipelineIntegrat │  │
│  │ (unit/integrat │  │ (secrets,      │  │ or               │  │
│  │  ion tests)    │  │  injections)   │  │ (Git/CI-CD/PR)   │  │
│  └────────────────┘  └────────────────┘  └──────────────────┘  │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ PRGenerator    │  │ DocGenerator   │  │ Microservice     │  │
│  │ (PR descriptions│  │ (migration     │  │ Decomposer       │  │
│  │  & changelogs) │  │  reports, API) │  │ (boundary analysis│ │
│  └────────────────┘  └────────────────┘  └──────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP API (all model calls)
┌───────────────────────────▼─────────────────────────────────────┐
│                    fusion-mlx (/v1/chat/completions)              │
│                    Apple Silicon MLX Runtime                     │
└─────────────────────────────────────────────────────────────────┘
```

### Key Modules

| Module | File | Description |
|--------|------|-------------|
| **Dependency Analyzer** | `analyzer/dependency.py` | Code dependency graph, dead code detection, tech debt estimation |
| **Code Transpiler** | `migration/transpiler.py` | Cross-language migration (COBOL→Java, VB6→C#, etc.) |
| **Incremental Refactorer** | `refactor/refactorer.py` | Test-first refactoring with dual-run verification |
| **Test Generator** | `test_gen/generator.py` | Unit and integration test generation |
| **Security Scanner** | `security/scanner.py` | Hardcoded secrets, injection vulnerabilities, CVE detection |
| **Pipeline Integrator** | `pipeline/__init__.py` | Git/CI-CD integration, PR creation, audit logging |
| **Priority Scorer** | `pipeline/__init__.py` | Migration priority scoring (business + tech debt) |
| **PR Generator** | `pr_gen/__init__.py` | PR description and changelog generation |
| **Doc Generator** | `pr_gen/__init__.py` | Migration reports and API documentation |
| **Microservice Decomposer** | `pr_gen/__init__.py` | Monolith boundary analysis and microservice suggestions |

---

## Comparison with Claude Code Modernization

| Capability | Claude Code | Fusion-Code-Modelization |
|------------|-------------|--------------------------|
| Code dependency analysis | ✅ | ✅ |
| Dead code detection | ✅ | ✅ |
| Tech debt estimation | ✅ | ✅ |
| Cross-language migration | ✅ COBOL→Java, etc. | ✅ COBOL→Java, VB6→C#, etc. |
| Test-first refactoring | ✅ | ✅ |
| Dual-run verification | ✅ | ✅ |
| Unit test generation | ✅ | ✅ |
| Security vulnerability scanning | ✅ | ✅ |
| Enterprise pipeline (Git/CI-CD) | ✅ | ✅ |
| Migration priority scoring | ✅ | ✅ |
| Microservice decomposition | ✅ | ✅ |
| Audit logging | ✅ | ✅ |
| **Local offline** | ❌ Cloud-only | ✅ **100% local** |
| **Data privacy** | ❌ Code uploaded to cloud | ✅ **Data never leaves device** |
| **China compliance** | ❌ Violates data security law | ✅ **Full compliance** |
| **Zero API cost** | ❌ Enterprise subscription | ✅ **Free** |
| **Gitee/GitLab support** | ❌ GitHub only | ✅ **All platforms** |

---

## Development

```bash
# Install dev dependencies
pip install -e ".[test]"

# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=fusion_code_modelization
```

### Test Stats
- **70 tests**, 0 failures
- **96%+ statement coverage**
- **Python 3.12+** compatible

---

## License

MIT

## Acknowledgments

- [fusion-mlx](https://github.com/dahai80/fusion-mlx) — Apple Silicon model serving
- [Claude Code Modernization](https://docs.anthropic.com/en/docs/claude-code) — Reference architecture