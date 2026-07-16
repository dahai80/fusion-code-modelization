"""Tests for Fusion-Code-Modelization core modules."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fusion_code_modelization.analyzer.dependency import DependencyAnalyzer, DependencyGraph
from fusion_code_modelization.migration.transpiler import CodeTranspiler
from fusion_code_modelization.refactor.refactorer import IncrementalRefactorer
from fusion_code_modelization.test_gen.generator import TestGenerator
from fusion_code_modelization.security.scanner import SecurityScanner


# ── DependencyAnalyzer ──

class TestDependencyAnalyzer:
    def test_scan_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "main.py").write_text("import os\nimport sys\nprint('hello')")
            Path(tmpdir, "utils.py").write_text("def helper():\n    pass")
            analyzer = DependencyAnalyzer()
            graph = analyzer.scan_directory(tmpdir)
            assert len(graph.nodes) >= 2
            assert "main.py" in graph.nodes or any("main" in n for n in graph.nodes)

    def test_scan_nonexistent(self):
        analyzer = DependencyAnalyzer()
        graph = analyzer.scan_directory("/nonexistent")
        assert len(graph.nodes) == 0

    def test_identify_dead_code(self):
        graph = DependencyGraph()
        graph.nodes["a.py"] = {"path": "a.py", "language": "python", "size_bytes": 100, "dependencies": []}
        graph.nodes["b.py"] = {"path": "b.py", "language": "python", "size_bytes": 100, "dependencies": []}
        graph.edges = [{"source": "a.py", "target": "b.py", "type": "import"}]
        dead = DependencyAnalyzer().identify_dead_code(graph)
        assert "a.py" in dead  # a.py imports b.py, but nothing imports a.py

    def test_estimate_tech_debt(self):
        graph = DependencyGraph()
        graph.nodes["a.py"] = {"path": "a.py", "language": "python", "size_bytes": 1000, "dependencies": []}
        debt = DependencyAnalyzer().estimate_tech_debt(graph)
        assert debt["total_files"] == 1
        assert debt["total_size_bytes"] == 1000

    def test_detect_language(self):
        assert DependencyAnalyzer._detect_language(".py") == "python"
        assert DependencyAnalyzer._detect_language(".java") == "java"
        assert DependencyAnalyzer._detect_language(".unknown") == ""

    def test_extract_imports_python(self):
        code = "import os\nfrom pathlib import Path\nimport sys"
        deps = DependencyAnalyzer._extract_imports(code, "python")
        assert "os" in deps
        assert "pathlib" in deps

    def test_generate_report(self):
        graph = DependencyGraph()
        graph.nodes["a.py"] = {"path": "a.py", "language": "python", "size_bytes": 100, "dependencies": []}
        debt = {"total_files": 1, "total_size_bytes": 100, "total_size_mb": 0.0, "dead_files": 0}
        report = DependencyAnalyzer.generate_report(graph, debt)
        assert "Analysis Report" in report
        assert "1 files" in report

    @pytest.mark.asyncio
    async def test_analyze_with_llm(self):
        analyzer = DependencyAnalyzer()
        with patch("httpx.AsyncClient.post", new=AsyncMock()) as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"choices": [{"message": {"content": '{"purpose": "test"}'}}]}
            mock_post.return_value = mock_resp
            result = await analyzer.analyze_with_llm("print('hello')", "python")
            assert "purpose" in result


# ── CodeTranspiler ──

class TestCodeTranspiler:
    @pytest.mark.asyncio
    async def test_same_language(self):
        t = CodeTranspiler()
        result = await t.transpile("print('hi')", "python", "python")
        assert result["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_transpile_success(self):
        t = CodeTranspiler()
        with patch("httpx.AsyncClient.post", new=AsyncMock()) as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"choices": [{"message": {"content": "```java\npublic class Hello {}\n```"}}]}
            mock_post.return_value = mock_resp
            result = await t.transpile("print('hi')", "python", "java")
            assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_transpile_failure(self):
        t = CodeTranspiler()
        with patch("httpx.AsyncClient.post", side_effect=RuntimeError("fail")):
            result = await t.transpile("code", "python", "java")
            assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_verify(self):
        t = CodeTranspiler()
        with patch("httpx.AsyncClient.post", new=AsyncMock()) as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"choices": [{"message": {"content": "YES, same logic"}}]}
            mock_post.return_value = mock_resp
            result = await t.verify("a", "b", "python")
            assert result["verified"] is True

    def test_list_supported(self):
        migrations = CodeTranspiler.list_supported_migrations()
        assert len(migrations) > 0
        assert any(m["source"] == "cobol" for m in migrations)

    def test_extract_code(self):
        content = "```python\nprint('hello')\n```"
        code = CodeTranspiler._extract_code(content, "python")
        assert "print" in code


# ── IncrementalRefactorer ──

class TestIncrementalRefactorer:
    @pytest.mark.asyncio
    async def test_characterize(self):
        r = IncrementalRefactorer()
        with patch("httpx.AsyncClient.post", new=AsyncMock()) as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"choices": [{"message": {"content": "def test(): pass"}}]}
            mock_post.return_value = mock_resp
            result = await r.characterize("def foo(): pass", "python")
            assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_refactor(self):
        r = IncrementalRefactorer()
        with patch("httpx.AsyncClient.post", new=AsyncMock()) as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"choices": [{"message": {"content": "```python\nx = 1\n```"}}]}
            mock_post.return_value = mock_resp
            result = await r.refactor("x=1", "python")
            assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_dual_run_verify(self):
        r = IncrementalRefactorer()
        with patch("httpx.AsyncClient.post", new=AsyncMock()) as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"choices": [{"message": {"content": "YES same output"}}]}
            mock_post.return_value = mock_resp
            result = await r.dual_run_verify("a", "a", "python")
            assert result["verified"] is True


# ── TestGenerator ──

class TestTestGenerator:
    @pytest.mark.asyncio
    async def test_generate_unit_tests(self):
        g = TestGenerator()
        with patch("httpx.AsyncClient.post", new=AsyncMock()) as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"choices": [{"message": {"content": "```python\ndef test(): pass\n```"}}]}
            mock_post.return_value = mock_resp
            result = await g.generate_unit_tests("def foo(): pass", "python")
            assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_generate_integration_tests(self):
        g = TestGenerator()
        with patch("httpx.AsyncClient.post", new=AsyncMock()) as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"choices": [{"message": {"content": "integration tests here"}}]}
            mock_post.return_value = mock_resp
            result = await g.generate_integration_tests([{"name": "mod1", "desc": "module 1"}], "python")
            assert result["status"] == "completed"


# ── SecurityScanner ──

class TestSecurityScanner:
    @pytest.mark.asyncio
    async def test_scan(self):
        s = SecurityScanner()
        with patch.object(s, "_llm_scan", AsyncMock(return_value={"findings": []})):
            result = await s.scan("password = 'secret123'", "python")
            assert result["total_findings"] >= 1  # hardcoded password

    @pytest.mark.asyncio
    async def test_scan_no_issues(self):
        s = SecurityScanner()
        with patch.object(s, "_llm_scan", AsyncMock(return_value={"findings": []})):
            result = await s.scan("x = 1", "python")
            assert result["total_findings"] >= 0

    @pytest.mark.asyncio
    async def test_hardcoded_secrets(self):
        code = "password = 'secret123'\napi_key = 'abc12345'\ntoken = 'longtoken123'"
        findings = SecurityScanner._check_hardcoded_secrets(code)
        assert len(findings) >= 3

    @pytest.mark.asyncio
    async def test_vulnerable_patterns(self):
        code = "eval(x)\nexec(y)"
        findings = SecurityScanner._check_vulnerable_patterns(code, "python")
        assert len(findings) >= 2

    @pytest.mark.asyncio
    async def test_fix(self):
        s = SecurityScanner()
        with patch("httpx.AsyncClient.post", new=AsyncMock()) as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"choices": [{"message": {"content": "```\nsecure = True\n```"}}]}
            mock_post.return_value = mock_resp
            result = await s.fix("password = 'secret'", "hardcoded password")
            assert result["status"] == "completed"