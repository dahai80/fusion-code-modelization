# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fusion-Code-Modelization is a local-first legacy code modernization and cross-language migration platform. All LLM inference goes through **fusion-mlx** (`localhost:11434`) — never calls OpenAI, Anthropic, or any cloud AI service directly.

## Build & Test

```bash
source /Users/dahai/fusion/.venv/bin/activate   # shared monorepo venv
pip install -e ".[test]"                          # install with test deps
pytest tests/                                     # run all tests
pytest tests/test_core.py::TestDependencyAnalyzer::test_scan_directory -v  # single test
pytest tests/ --cov=fusion_code_modelization       # with coverage
```

## Architecture

Single Python package `fusion_code_modelization` with 9 submodules, each a standalone class that calls fusion-mlx via `httpx.AsyncClient`:

| Submodule | Class(es) | Purpose |
|-----------|-----------|---------|
| `analyzer/dependency.py` | `DependencyAnalyzer`, `DependencyGraph` | Build dependency graphs, detect dead code, estimate tech debt |
| `migration/transpiler.py` | `CodeTranspiler` | Cross-language migration (COBOL→Java, VB6→C#, etc.) |
| `refactor/refactorer.py` | `IncrementalRefactorer` | Test-first refactoring with dual-run verification |
| `test_gen/generator.py` | `TestGenerator` | Unit/integration test generation |
| `security/scanner.py` | `SecurityScanner` | Static pattern + LLM-powered vulnerability scanning |
| `pipeline/__init__.py` | `PipelineIntegrator`, `PriorityScorer`, `AuditLog` | Git PR creation, CI/CD config generation, audit logging |
| `pr_gen/__init__.py` | `PRGenerator`, `DocGenerator`, `MicroserviceDecomposer` | PR descriptions, migration reports, microservice boundary analysis |
| `decompose/__init__.py` | *(empty)* | Placeholder |
| `doc_gen/__init__.py` | *(empty)* | Placeholder |

All LLM-calling classes accept `mlx_url` param (default `http://localhost:11434/v1`) and use model `qwen3.5-9b` with low temperature (0.0–0.3). The pipeline module (`PipelineIntegrator`, `PriorityScorer`, `AuditLog`) is the only one that does **not** call the LLM — it's pure local logic (git ops, scoring, audit).

## CLI

Entry point `fusion-code-modelization` defined in `cli/__init__.py:main()`. Subcommands: `analyze`, `transpile`, `refactor`, `test-gen`, `security`, `version`.

## Key Patterns

- Every LLM response is parsed via `_extract_code(content)` — regex extracts code from markdown fences, falls back to raw content
- All async methods return `dict[str, Any]` with `"status": "completed" | "failed"` + result/error fields
- Static analysis methods (import extraction, secret detection, vulnerability patterns) are pure regex with no LLM dependency
- Tests mock `httpx.AsyncClient.post` via `unittest.mock.AsyncMock`; no real fusion-mlx calls in test suite
