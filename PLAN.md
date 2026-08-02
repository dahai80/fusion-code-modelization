# Phase 5 (V2.5) Implementation Plan

<!-- GateGuard: Updated file. Importers: dev planning. Affected API: none. Data schemas: none. User instruction: "启动下一个阶段的实施" — implement Phase 5 per architecture compliance and quality maturity. -->

## Current State

- v0.4.0 with 438 tests, 24 submodules, 107 public API symbols, ruff clean, CI green
- 5 V2.0 modules delivered: benchmark, loadbalancer, offline, trace, agent_comm
- Architecture compliance audit (ARCHITECTURE_COMPLIANCE.md) flags 3 P1 violations
- 8 modules lack dedicated test files (analyzer, migration, pipeline, pr_gen, refactor, security, test_gen, cli)
- decompose/ and doc_gen/ have all code in __init__.py (no separation)
- pyproject.toml name has typo: "modenization" → should be "modernization"

## Phase 5 Goals: Quality Maturity + Architecture Compliance

### 1. Architecture Compliance Remediation (P1)
Per ARCHITECTURE_COMPLIANCE.md violations:

| # | Violation | Fix |
|---|-----------|-----|
| 1 | 名称名实不符 "modenization" | Fix typo → "modernization" in pyproject.toml, update package references |
| 2 | SecurityScanner 与 fusion-security 重叠 | Refactor: keep static pattern scanning (secrets, vuln patterns), remove LLM scan overlap, add `fusion_security_api_url` option for delegation |
| 3 | MicroserviceDecomposer 定位不清 | Keep as L4 工具, add `boundary_type` enum (MICROSERVICE, MODULE, PACKAGE) for multi-granularity |

### 2. Test Coverage Completion
Dedicated test files for 8 modules currently relying on legacy test files:

| Module | Current Coverage | Target |
|--------|-----------------|--------|
| `analyzer/dependency.py` | test_coverage.py (shared) | test_analyzer.py |
| `migration/transpiler.py` | test_advanced.py (shared) | test_migration.py |
| `refactor/refactorer.py` | test_coverage.py (shared) | test_refactor.py |
| `test_gen/generator.py` | test_advanced.py (shared) | test_test_gen.py |
| `security/scanner.py` | test_coverage.py (shared) | test_security.py |
| `pipeline/__init__.py` | test_coverage.py + test_final.py | test_pipeline.py |
| `pr_gen/__init__.py` | test_advanced.py (shared) | test_pr_gen.py |
| `cli/__init__.py` | test_advanced.py (shared) | test_cli.py |

After migration → delete test_advanced.py, test_coverage.py, test_final.py (or merge unique tests).

### 3. Module Structure Cleanup
- `decompose/__init__.py` → split into `models.py` + `detector.py`
- `doc_gen/__init__.py` → split into `models.py` + `generator.py`
- `pipeline/__init__.py` → split into `integrator.py` (move PipelineIntegrator class out)
- `pr_gen/__init__.py` → split into `pr_generator.py` + `doc_generator.py` + `decomposer.py`

### 4. Cross-Module Integration Tests
- Benchmark + Trace: verify benchmark results are traceable
- LoadBalancer + ClusterScheduler: end-to-end smart dispatch
- Offline + Core: OfflineConfig restricts model routing
- AgentComm + Cluster: cross-node collaboration scheduling
- Pipeline + Trace: full pipeline artifact traceability

### 5. CLI Hardening
- Add `--json` output flag to all commands
- Add `--verbose`/`--quiet` log level control
- Error exit codes: 0=success, 1=error, 2=invalid-args

### 6. CI Enhancement
- Add coverage threshold (minimum 80%)
- Add mypy type-checking job
- Add security scan job (bandit)

## Version Bump: 0.4.0 → 0.5.0

## Implementation Order

1. **Architecture compliance** — Fix typo, refactor SecurityScanner, clarify MicroserviceDecomposer
2. **Module structure cleanup** — Split __init__.py monoliths into proper module files
3. **Dedicated test files** — Migrate tests from legacy files, delete legacy files
4. **Cross-module integration tests** — End-to-end validation
5. **CLI hardening** — JSON output, exit codes, log levels
6. **CI enhancement** — Coverage threshold, type checking, security scan
7. **README/docs update** — Reflect new structure
8. **Final verification** — All green, commit, tag v0.5.0

## Estimated Scope

- ~12 file renames/splits (module structure)
- ~8 new test files + 3 legacy file deletions
- ~5 integration test cases
- ~3 CI job additions
- ~2 existing module refactors (security, decompose)
- Version 0.5.0
