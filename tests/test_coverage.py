# GateGuard: Importers: none (test file). Affected API: none. Data schemas: none. User instruction: Phase 6 — add streaming tests.
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from fusion_code_modelization.analyzer.dependency import DependencyAnalyzer
from fusion_code_modelization.core.client import MLXClient
from fusion_code_modelization.migration.transpiler import CodeTranspiler
from fusion_code_modelization.pipeline import PipelineIntegrator
from fusion_code_modelization.refactor.refactorer import IncrementalRefactorer
from fusion_code_modelization.security.scanner import SecurityScanner

# ── CLI Tests ──


class TestCLI:
    def test_version(self):
        from fusion_code_modelization.cli import main

        with patch.object(sys, "argv", ["fusion-code-modelization", "version"]):
            main()

    def test_analyze(self):
        from fusion_code_modelization.cli import main

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "test.py").write_text("import os\nprint('hello')")
            with patch.object(sys, "argv", ["fusion-code-modelization", "analyze", tmpdir]):
                main()

    def test_analyze_with_output(self):
        from fusion_code_modelization.cli import main

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "test.py").write_text("import os")
            out = str(Path(tmpdir) / "report.md")
            with patch.object(sys, "argv", ["fusion-code-modelization", "analyze", tmpdir, "--output=" + out]):
                main()
            assert Path(out).exists()

    def test_transpile(self):
        from fusion_code_modelization.cli import main

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.object(
                sys,
                "argv",
                ["fusion-code-modelization", "transpile", str(Path(tmpdir, "test.py")), "--from=python", "--to=java"],
            ),
            patch(
                "fusion_code_modelization.migration.transpiler.CodeTranspiler.transpile",
                AsyncMock(return_value={"status": "completed", "code": "public class X {}"}),
            ),
        ):
            Path(tmpdir, "test.py").write_text("print('hello')")
            main()

    def test_transpile_with_output(self):
        from fusion_code_modelization.cli import main

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.object(
                sys,
                "argv",
                [
                    "fusion-code-modelization",
                    "transpile",
                    str(Path(tmpdir, "test.py")),
                    "--from=python",
                    "--to=java",
                    "--output=" + str(Path(tmpdir) / "output.java"),
                ],
            ),
            patch(
                "fusion_code_modelization.migration.transpiler.CodeTranspiler.transpile",
                AsyncMock(return_value={"status": "completed", "code": "public class X {}"}),
            ),
        ):
            Path(tmpdir, "test.py").write_text("print('hello')")
            main()
            assert Path(tmpdir, "output.java").exists()

    def test_transpile_failure(self):
        from fusion_code_modelization.cli import main

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.object(
                sys,
                "argv",
                ["fusion-code-modelization", "transpile", str(Path(tmpdir, "test.py")), "--from=python", "--to=java"],
            ),
            patch(
                "fusion_code_modelization.migration.transpiler.CodeTranspiler.transpile",
                AsyncMock(return_value={"status": "failed", "error": "API error"}),
            ),
        ):
            Path(tmpdir, "test.py").write_text("print('hello')")
            main()

    def test_refactor(self):
        from fusion_code_modelization.cli import main

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.object(sys, "argv", ["fusion-code-modelization", "refactor", str(Path(tmpdir, "test.py"))]),
            patch(
                "fusion_code_modelization.refactor.refactorer.IncrementalRefactorer.refactor",
                AsyncMock(return_value={"status": "completed", "refactored": "x = 1"}),
            ),
        ):
            Path(tmpdir, "test.py").write_text("x=1")
            main()

    def test_refactor_with_output(self):
        from fusion_code_modelization.cli import main

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.object(
                sys,
                "argv",
                [
                    "fusion-code-modelization",
                    "refactor",
                    str(Path(tmpdir, "test.py")),
                    "--output=" + str(Path(tmpdir) / "refactored.py"),
                ],
            ),
            patch(
                "fusion_code_modelization.refactor.refactorer.IncrementalRefactorer.refactor",
                AsyncMock(return_value={"status": "completed", "refactored": "x = 1"}),
            ),
        ):
            Path(tmpdir, "test.py").write_text("x=1")
            main()
            assert Path(tmpdir, "refactored.py").exists()

    def test_test_gen(self):
        from fusion_code_modelization.cli import main

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.object(sys, "argv", ["fusion-code-modelization", "test-gen", str(Path(tmpdir, "test.py"))]),
            patch(
                "fusion_code_modelization.test_gen.generator.UnitTestGenerator.generate_unit_tests",
                AsyncMock(return_value={"status": "completed", "tests": "def test(): pass"}),
            ),
        ):
            Path(tmpdir, "test.py").write_text("def foo(): pass")
            main()

    def test_test_gen_with_output(self):
        from fusion_code_modelization.cli import main

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.object(
                sys,
                "argv",
                [
                    "fusion-code-modelization",
                    "test-gen",
                    str(Path(tmpdir, "test.py")),
                    "--output=" + str(Path(tmpdir) / "test_output.py"),
                ],
            ),
            patch(
                "fusion_code_modelization.test_gen.generator.UnitTestGenerator.generate_unit_tests",
                AsyncMock(return_value={"status": "completed", "tests": "def test(): pass"}),
            ),
        ):
            Path(tmpdir, "test.py").write_text("def foo(): pass")
            main()
            assert Path(tmpdir, "test_output.py").exists()

    def test_security(self):
        from fusion_code_modelization.cli import main

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.object(sys, "argv", ["fusion-code-modelization", "security", str(Path(tmpdir, "test.py"))]),
            patch(
                "fusion_code_modelization.security.scanner.SecurityScanner.scan",
                AsyncMock(
                    return_value={
                        "total_findings": 1,
                        "findings": [{"severity": "high", "line": 1, "description": "test"}],
                    }
                ),
            ),
        ):
            Path(tmpdir, "test.py").write_text("password = 'secret123'")
            main()

    def test_security_with_output(self):
        from fusion_code_modelization.cli import main

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.object(
                sys,
                "argv",
                [
                    "fusion-code-modelization",
                    "security",
                    str(Path(tmpdir, "test.py")),
                    "--output=" + str(Path(tmpdir) / "security.json"),
                ],
            ),
            patch(
                "fusion_code_modelization.security.scanner.SecurityScanner.scan",
                AsyncMock(return_value={"total_findings": 1, "findings": []}),
            ),
        ):
            Path(tmpdir, "test.py").write_text("password = 'secret123'")
            main()


# ── Pipeline Coverage ──


class TestPipelineCoverage:
    def test_generate_ci_config_unknown(self):
        pi = PipelineIntegrator()
        config = pi.generate_ci_config("unknown")
        assert "python" in config.get(".github/workflows/ci.yml", "")

    def test_audit_log_limit(self):
        pi = PipelineIntegrator()
        for i in range(60):
            pi._log(f"action{i}", "core", "f.py", "success")
        logs = pi.get_audit_log(limit=10)
        assert len(logs) == 10

    def test_export_audit_log_no_path(self):
        pi = PipelineIntegrator()
        pi._log("test", "core", "f.py", "success")
        result = pi.export_audit_log()
        data = json.loads(result)
        assert len(data) == 1


# ── Security Scanner Coverage ──


class TestSecurityCoverage:
    @pytest.mark.asyncio
    async def test_llm_scan(self):
        s = SecurityScanner()
        with patch.object(
            s._client,
            "chat",
            new=AsyncMock(
                return_value={
                    "status": "completed",
                    "content": '[{"type": "sql_injection", "severity": "high", "line": 1, "description": "test"}]',
                }
            ),
        ):
            result = await s._llm_scan("select * from users", "python")
            assert len(result.get("findings", [])) >= 1

    @pytest.mark.asyncio
    async def test_llm_scan_invalid_json(self):
        s = SecurityScanner()
        with patch.object(
            s._client, "chat", new=AsyncMock(return_value={"status": "completed", "content": "not json"})
        ):
            result = await s._llm_scan("code", "python")
            assert result.get("findings") == []

    @pytest.mark.asyncio
    async def test_vulnerable_patterns_java(self):
        code = 'Runtime.getRuntime().exec("ls")'
        findings = SecurityScanner._check_vulnerable_patterns(code, "java")
        assert len(findings) >= 1

    @pytest.mark.asyncio
    async def test_vulnerable_patterns_javascript(self):
        code = 'element.innerHTML = "test"'
        findings = SecurityScanner._check_vulnerable_patterns(code, "javascript")
        assert len(findings) >= 1


# ── Refactorer Coverage ──


class TestRefactorCoverage:
    @pytest.mark.asyncio
    async def test_characterize_failure(self):
        r = IncrementalRefactorer()
        with patch.object(r._client, "chat", new=AsyncMock(return_value={"status": "failed", "error": "fail"})):
            result = await r.characterize("code", "python")
            assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_refactor_failure(self):
        r = IncrementalRefactorer()
        with patch.object(r._client, "chat", new=AsyncMock(return_value={"status": "failed", "error": "fail"})):
            result = await r.refactor("code", "python")
            assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_dual_run_verify_failure(self):
        r = IncrementalRefactorer()
        with patch.object(r._client, "chat", new=AsyncMock(return_value={"status": "failed", "error": "fail"})):
            result = await r.dual_run_verify("a", "b", "python")
            assert result["verified"] is False


# ── Analyzer Coverage ──


class TestAnalyzerCoverage:
    @pytest.mark.asyncio
    async def test_analyze_with_llm_failure(self):
        a = DependencyAnalyzer()
        with patch.object(a._client, "chat", new=AsyncMock(return_value={"status": "failed", "error": "fail"})):
            result = await a.analyze_with_llm("code", "python")
            assert "error" in result


# ── Transpiler Coverage ──


class TestTranspilerCoverage:
    def test_extract_code_no_code_block(self):
        code = MLXClient.extract_code("just plain text", "python")
        assert code == "just plain text"

    @pytest.mark.asyncio
    async def test_verify_failure(self):
        t = CodeTranspiler()
        with patch.object(t._client, "chat", new=AsyncMock(return_value={"status": "failed", "error": "fail"})):
            result = await t.verify("a", "b", "python")
            assert result["verified"] is False


# ── Streaming Coverage ──


async def _fake_chat_stream(tokens):
    async def _gen(**__):
        for t in tokens:
            yield t

    return _gen


class TestTranspilerStream:
    @pytest.mark.asyncio
    async def test_transpile_stream_success(self):
        t = CodeTranspiler()
        with patch.object(t._client, "chat_stream", new=await _fake_chat_stream(["```python\n", "x=1\n", "```"])):
            chunks = []
            async for chunk in t.transpile_stream("code", "java", "python"):
                chunks.append(chunk)
            tokens_list = [c for c in chunks if c["type"] == "token"]
            done = [c for c in chunks if c["type"] == "done"]
            assert len(tokens_list) == 3
            assert len(done) == 1
            assert done[0]["result"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_transpile_stream_same_lang(self):
        t = CodeTranspiler()
        chunks = []
        async for chunk in t.transpile_stream("code", "python", "python"):
            chunks.append(chunk)
        assert chunks[0]["result"]["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_transpile_stream_error(self):
        t = CodeTranspiler()

        async def _err(**__):
            raise RuntimeError("boom")
            yield

        with patch.object(t._client, "chat_stream", new=_err):
            chunks = []
            async for chunk in t.transpile_stream("code", "java", "python"):
                chunks.append(chunk)
            done = [c for c in chunks if c["type"] == "done"]
            assert done[0]["result"]["status"] == "failed"


class TestRefactorStream:
    @pytest.mark.asyncio
    async def test_refactor_stream_success(self):
        r = IncrementalRefactorer()
        with patch.object(r._client, "chat_stream", new=await _fake_chat_stream(["```python\n", "y=2\n", "```"])):
            chunks = []
            async for chunk in r.refactor_stream("code", "python"):
                chunks.append(chunk)
            done = [c for c in chunks if c["type"] == "done"]
            assert done[0]["result"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_refactor_stream_error(self):
        r = IncrementalRefactorer()

        async def _err(**__):
            raise RuntimeError("boom")
            yield

        with patch.object(r._client, "chat_stream", new=_err):
            chunks = []
            async for chunk in r.refactor_stream("code", "python"):
                chunks.append(chunk)
            done = [c for c in chunks if c["type"] == "done"]
            assert done[0]["result"]["status"] == "failed"


class TestUnitTestGeneratorStream:
    @pytest.mark.asyncio
    async def test_generate_unit_tests_stream_success(self):
        from fusion_code_modelization.test_gen.generator import UnitTestGenerator

        g = UnitTestGenerator()
        with patch.object(
            g._client, "chat_stream", new=await _fake_chat_stream(["```python\n", "def test_x(): pass\n", "```"])
        ):
            chunks = []
            async for chunk in g.generate_unit_tests_stream("code", "python"):
                chunks.append(chunk)
            done = [c for c in chunks if c["type"] == "done"]
            assert done[0]["result"]["status"] == "completed"
            assert "test_x" in done[0]["result"]["tests"]

    @pytest.mark.asyncio
    async def test_generate_unit_tests_stream_error(self):
        from fusion_code_modelization.test_gen.generator import UnitTestGenerator

        g = UnitTestGenerator()

        async def _err(**__):
            raise RuntimeError("boom")
            yield

        with patch.object(g._client, "chat_stream", new=_err):
            chunks = []
            async for chunk in g.generate_unit_tests_stream("code", "python"):
                chunks.append(chunk)
            done = [c for c in chunks if c["type"] == "done"]
            assert done[0]["result"]["status"] == "failed"


class TestSecurityScannerStream:
    @pytest.mark.asyncio
    async def test_scan_stream_static_only(self):
        from fusion_code_modelization.security.scanner import SecurityScanner

        s = SecurityScanner(static_only=True)
        code = 'password = "secret"'
        chunks = []
        async for chunk in s.scan_stream(code, "python"):
            chunks.append(chunk)
        findings_chunks = [c for c in chunks if c["type"] == "findings"]
        done = [c for c in chunks if c["type"] == "done"]
        assert len(findings_chunks) >= 1
        assert done[0]["result"]["scan_mode"] == "static"

    @pytest.mark.asyncio
    async def test_scan_stream_with_llm(self):
        from fusion_code_modelization.security.scanner import SecurityScanner

        s = SecurityScanner(mlx_url="http://localhost:11434/v1", static_only=False)
        with patch.object(
            s._client,
            "chat_stream",
            new=await _fake_chat_stream(['[{"type":"xss","severity":"high","line":1,"description":"XSS"}]']),
        ):
            chunks = []
            async for chunk in s.scan_stream("code", "javascript"):
                chunks.append(chunk)
            done = [c for c in chunks if c["type"] == "done"]
            assert done[0]["result"]["scan_mode"] == "static+llm"
            assert done[0]["result"]["total_findings"] >= 1


class TestDocGenStream:
    @pytest.mark.asyncio
    async def test_generate_docs_stream_success(self):
        from fusion_code_modelization.doc_gen import DocumentationGenerator

        g = DocumentationGenerator(mlx_url="http://localhost:11434/v1")
        with patch.object(g._client, "chat_stream", new=await _fake_chat_stream(["# Module Docs\n", "Some text\n"])):
            chunks = []
            async for chunk in g.generate_docs_stream("code", "python"):
                chunks.append(chunk)
            done = [c for c in chunks if c["type"] == "done"]
            assert done[0]["result"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_generate_docs_stream_error(self):
        from fusion_code_modelization.doc_gen import DocumentationGenerator

        g = DocumentationGenerator(mlx_url="http://localhost:11434/v1")

        async def _err(**__):
            raise RuntimeError("boom")
            yield

        with patch.object(g._client, "chat_stream", new=_err):
            chunks = []
            async for chunk in g.generate_docs_stream("code", "python"):
                chunks.append(chunk)
            done = [c for c in chunks if c["type"] == "done"]
            assert done[0]["result"]["status"] == "failed"
