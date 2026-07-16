# Fusion-Code-Modelization API Reference

---

## `fusion_code_modelization.analyzer.dependency`

```python
from fusion_code_modelization.analyzer.dependency import DependencyAnalyzer, DependencyGraph
```

### DependencyGraph
| Field | Type | Description |
|-------|------|-------------|
| `nodes` | `dict[str, dict]` | Module nodes with path, language, size |
| `edges` | `list[dict]` | Dependency edges with source/target/type |

### DependencyAnalyzer
| Method | Returns | Description |
|--------|---------|-------------|
| `scan_directory(path, language)` | `DependencyGraph` | Build dependency graph from directory |
| `identify_dead_code(graph)` | `list[str]` | Find modules with no incoming deps |
| `estimate_tech_debt(graph)` | `dict` | Total files, size, dead code count |
| `analyze_with_llm(code, language)` | `dict` | LLM-powered code analysis |
| `generate_report(graph, tech_debt)` | `str` | Markdown analysis report |

---

## `fusion_code_modelization.migration.transpiler`

```python
from fusion_code_modelization.migration.transpiler import CodeTranspiler
```

| Method | Returns | Description |
|--------|---------|-------------|
| `transpile(code, source_lang, target_lang)` | `dict` | Cross-language code migration |
| `verify(original, transpiled, language)` | `dict` | Verify logic preservation |
| `list_supported_migrations()` | `list[dict]` | List all supported language pairs |

---

## `fusion_code_modelization.refactor.refactorer`

```python
from fusion_code_modelization.refactor.refactorer import IncrementalRefactorer
```

| Method | Returns | Description |
|--------|---------|-------------|
| `characterize(code, language)` | `dict` | Generate characterization tests |
| `refactor(code, language, instructions)` | `dict` | Refactor code preserving behavior |
| `dual_run_verify(original, refactored, language)` | `dict` | Verify output consistency |

---

## `fusion_code_modelization.test_gen.generator`

```python
from fusion_code_modelization.test_gen.generator import TestGenerator
```

| Method | Returns | Description |
|--------|---------|-------------|
| `generate_unit_tests(code, language)` | `dict` | Generate unit tests with edge cases |
| `generate_integration_tests(components, language)` | `dict` | Generate integration tests |

---

## `fusion_code_modelization.security.scanner`

```python
from fusion_code_modelization.security.scanner import SecurityScanner
```

| Method | Returns | Description |
|--------|---------|-------------|
| `scan(code, language)` | `dict` | Full security scan (static + LLM) |
| `fix(code, vulnerability)` | `dict` | Generate security fix |

---

## `fusion_code_modelization.pipeline`

```python
from fusion_code_modelization.pipeline import PipelineIntegrator, PriorityScorer, AuditLog
```

### PipelineIntegrator
| Method | Returns | Description |
|--------|---------|-------------|
| `create_pr(branch, title, description, changes)` | `dict` | Create Git branch with changes |
| `generate_ci_config(language)` | `dict` | Generate CI/CD workflow config |
| `get_audit_log(limit)` | `list[dict]` | Get audit log entries |
| `export_audit_log(output_path)` | `str` | Export audit log to JSON |

### PriorityScorer
| Method | Returns | Description |
|--------|---------|-------------|
| `score_file(file_info)` | `dict` | Score migration priority |

---

## `fusion_code_modelization.pr_gen`

```python
from fusion_code_modelization.pr_gen import PRGenerator, DocGenerator, MicroserviceDecomposer
```

### PRGenerator
| Method | Returns | Description |
|--------|---------|-------------|
| `generate_pr_description(changes)` | `dict` | Generate PR description |

### DocGenerator
| Method | Returns | Description |
|--------|---------|-------------|
| `generate_migration_report(analysis, results)` | `str` | Generate migration report |
| `generate_api_docs(code, language)` | `str` | Generate API documentation |

### MicroserviceDecomposer
| Method | Returns | Description |
|--------|---------|-------------|
| `analyze_boundaries(graph)` | `list[dict]` | Analyze service boundaries |
| `suggest_decomposition(code, language)` | `dict` | LLM-powered decomposition suggestions |