from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock, patch

import pytest

from fusion_code_modelization.core.client import MLXClient
from fusion_code_modelization.core.config import ModelConfig
from fusion_code_modelization.pr_gen.decomposer import BoundaryType
from fusion_code_modelization.security.scanner import SecurityScanner

logger = logging.getLogger(__name__)


class TestSecurityScanner:
    def test_init_default(self):
        s = SecurityScanner()
        assert s._client is not None
        assert s._fusion_security_url is None
        assert s._static_only is True

    def test_init_with_client(self):
        client = MLXClient(ModelConfig(base_url="http://custom:9999/v1"))
        s = SecurityScanner(client=client)
        assert s._client is client
        assert s._static_only is False

    def test_init_with_fusion_security_url(self):
        s = SecurityScanner(fusion_security_url="http://security:8080")
        assert s._fusion_security_url == "http://security:8080"
        assert s._static_only is False

    # ── scan_static (pure, no mock needed) ──

    def test_scan_static_clean_code(self):
        s = SecurityScanner()
        result = s.scan_static("x = 1\ny = 2", "python")
        assert result["status"] == "completed"
        assert result["total_findings"] == 0
        assert result["scan_mode"] == "static"
        assert result["language"] == "python"
        assert result["findings"] == []

    def test_scan_static_with_secrets(self):
        s = SecurityScanner()
        code = "password = 'secret123'\napi_key = 'abc12345'"
        result = s.scan_static(code, "python")
        assert result["status"] == "completed"
        assert result["total_findings"] >= 2
        assert result["scan_mode"] == "static"

    def test_scan_static_with_vulnerable_patterns(self):
        s = SecurityScanner()
        code = "eval(x)\nos.system('ls')"
        result = s.scan_static(code, "python")
        assert result["status"] == "completed"
        assert result["total_findings"] >= 2

    # ── _check_hardcoded_secrets ──

    def test_check_hardcoded_secrets_password(self):
        code = "password = 'mysecret'"
        findings = SecurityScanner._check_hardcoded_secrets(code)
        assert len(findings) == 1
        assert findings[0]["type"] == "hardcoded_secret"
        assert findings[0]["severity"] == "high"
        assert "password" in findings[0]["description"].lower()

    def test_check_hardcoded_secrets_passwd(self):
        code = "passwd = 'abc'"
        findings = SecurityScanner._check_hardcoded_secrets(code)
        assert len(findings) == 1

    def test_check_hardcoded_secrets_pwd(self):
        code = "pwd = 'xyz'"
        findings = SecurityScanner._check_hardcoded_secrets(code)
        assert len(findings) == 1

    def test_check_hardcoded_secrets_api_key(self):
        code = "api_key = 'sk-12345678'"
        findings = SecurityScanner._check_hardcoded_secrets(code)
        assert len(findings) == 1
        assert findings[0]["type"] == "hardcoded_secret"

    def test_check_hardcoded_secrets_apikey(self):
        code = "apikey = 'sk-12345678'"
        findings = SecurityScanner._check_hardcoded_secrets(code)
        assert len(findings) == 1

    def test_check_hardcoded_secrets_api_key_dash(self):
        code = "api-key = 'sk-12345678'"
        findings = SecurityScanner._check_hardcoded_secrets(code)
        assert len(findings) == 1

    def test_check_hardcoded_secrets_secret_long(self):
        code = "secret = 'alongsecretvalue'"
        findings = SecurityScanner._check_hardcoded_secrets(code)
        assert len(findings) >= 1

    def test_check_hardcoded_secrets_token_long(self):
        code = "token = 'bearer_token_value'"
        findings = SecurityScanner._check_hardcoded_secrets(code)
        assert len(findings) >= 1

    def test_check_hardcoded_secrets_token_short_ignored(self):
        code = "token = 'short'"
        findings = SecurityScanner._check_hardcoded_secrets(code)
        assert len(findings) == 0

    def test_check_hardcoded_secrets_private_key(self):
        code = "-----BEGIN RSA PRIVATE KEY-----\nMIIBogIBAAJBAKx1\n-----END RSA PRIVATE KEY-----"
        findings = SecurityScanner._check_hardcoded_secrets(code)
        assert len(findings) >= 1
        assert any("private key" in f["description"].lower() for f in findings)

    def test_check_hardcoded_secrets_ec_private_key(self):
        code = "-----BEGIN EC PRIVATE KEY-----\nMHQCAQEEI\n-----END EC PRIVATE KEY-----"
        findings = SecurityScanner._check_hardcoded_secrets(code)
        assert len(findings) >= 1

    def test_check_hardcoded_secrets_clean(self):
        code = "x = 1\nname = 'hello'"
        findings = SecurityScanner._check_hardcoded_secrets(code)
        assert findings == []

    def test_check_hardcoded_secrets_line_numbers(self):
        code = "x = 1\npassword = 'secret'\ny = 2"
        findings = SecurityScanner._check_hardcoded_secrets(code)
        assert len(findings) == 1
        assert findings[0]["line"] == 2

    def test_check_hardcoded_secrets_multiple_on_different_lines(self):
        code = "password = 'abc'\napi_key = 'sk-1234'\ntoken = 'longtokenvalue'"
        findings = SecurityScanner._check_hardcoded_secrets(code)
        assert len(findings) == 3
        lines = {f["line"] for f in findings}
        assert lines == {1, 2, 3}

    def test_check_hardcoded_secrets_case_insensitive(self):
        code = "PASSWORD = 'secret'\nAPI_KEY = 'key123'"
        findings = SecurityScanner._check_hardcoded_secrets(code)
        assert len(findings) == 2

    # ── _check_vulnerable_patterns ──

    def test_check_vulnerable_patterns_python_eval(self):
        code = "eval(user_input)"
        findings = SecurityScanner._check_vulnerable_patterns(code, "python")
        assert len(findings) == 1
        assert findings[0]["type"] == "vulnerable_pattern"
        assert findings[0]["severity"] == "medium"
        assert "eval" in findings[0]["description"].lower()

    def test_check_vulnerable_patterns_python_exec(self):
        code = "exec(code_string)"
        findings = SecurityScanner._check_vulnerable_patterns(code, "python")
        assert len(findings) == 1
        assert "exec" in findings[0]["description"].lower()

    def test_check_vulnerable_patterns_python_os_system(self):
        code = "os.system('rm -rf /')"
        findings = SecurityScanner._check_vulnerable_patterns(code, "python")
        assert len(findings) == 1
        assert "command injection" in findings[0]["description"].lower()

    def test_check_vulnerable_patterns_python_all_three(self):
        code = "eval(x)\nexec(y)\nos.system(cmd)"
        findings = SecurityScanner._check_vulnerable_patterns(code, "python")
        assert len(findings) == 3
        lines = {f["line"] for f in findings}
        assert lines == {1, 2, 3}

    def test_check_vulnerable_patterns_java_runtime_exec(self):
        code = "Runtime.getRuntime().exec(cmd)"
        findings = SecurityScanner._check_vulnerable_patterns(code, "java")
        assert len(findings) == 1
        assert "command injection" in findings[0]["description"].lower()

    def test_check_vulnerable_patterns_java_sql_injection(self):
        code = "Statement.executeQuery(sql)"
        findings = SecurityScanner._check_vulnerable_patterns(code, "java")
        assert len(findings) == 1
        assert "sql injection" in findings[0]["description"].lower()

    def test_check_vulnerable_patterns_javascript_innerhtml(self):
        code = "el.innerHTML = userInput"
        findings = SecurityScanner._check_vulnerable_patterns(code, "javascript")
        assert len(findings) == 1
        assert "xss" in findings[0]["description"].lower()

    def test_check_vulnerable_patterns_javascript_document_write(self):
        code = "document.write(html)"
        findings = SecurityScanner._check_vulnerable_patterns(code, "javascript")
        assert len(findings) == 1
        assert "xss" in findings[0]["description"].lower()

    def test_check_vulnerable_patterns_unknown_language(self):
        code = "eval(x)"
        findings = SecurityScanner._check_vulnerable_patterns(code, "cobol")
        assert findings == []

    def test_check_vulnerable_patterns_clean_code(self):
        code = "x = 1\nprint('hello')"
        findings = SecurityScanner._check_vulnerable_patterns(code, "python")
        assert findings == []

    def test_check_vulnerable_patterns_line_numbers(self):
        code = "x = 1\neval(x)\ny = 2"
        findings = SecurityScanner._check_vulnerable_patterns(code, "python")
        assert len(findings) == 1
        assert findings[0]["line"] == 2

    # ── scan (async, with LLM) ──

    @pytest.mark.asyncio
    async def test_scan_static_only_mode(self):
        s = SecurityScanner()
        result = await s.scan("x = 1", "python")
        assert result["status"] == "completed"
        assert result["scan_mode"] == "static"

    @pytest.mark.asyncio
    async def test_scan_with_llm_no_findings(self):
        s = SecurityScanner(client=MLXClient())
        with patch.object(
            s._client,
            "chat",
            new=AsyncMock(return_value={"status": "completed", "content": "[]"}),
        ):
            result = await s.scan("x = 1", "python")
            assert result["status"] == "completed"
            assert result["scan_mode"] == "static+llm"

    @pytest.mark.asyncio
    async def test_scan_with_llm_json_findings(self):
        s = SecurityScanner(client=MLXClient())
        llm_response = json.dumps(
            [
                {"type": "sql_injection", "severity": "high", "line": 5, "description": "unsafe SQL"},
            ]
        )
        with patch.object(
            s._client,
            "chat",
            new=AsyncMock(return_value={"status": "completed", "content": llm_response}),
        ):
            result = await s.scan("query = 'SELECT *'", "python")
            assert result["status"] == "completed"
            assert result["total_findings"] >= 1
            types = {f["type"] for f in result["findings"]}
            assert "sql_injection" in types

    @pytest.mark.asyncio
    async def test_scan_with_llm_static_plus_llm_findings(self):
        s = SecurityScanner(client=MLXClient())
        llm_response = json.dumps(
            [
                {"type": "xss", "severity": "high", "line": 1, "description": "reflected input"},
            ]
        )
        with patch.object(
            s._client,
            "chat",
            new=AsyncMock(return_value={"status": "completed", "content": llm_response}),
        ):
            code = "password = 'hardcoded'\neval(x)"
            result = await s.scan(code, "python")
            assert result["status"] == "completed"
            assert result["total_findings"] >= 3
            assert result["language"] == "python"

    @pytest.mark.asyncio
    async def test_scan_llm_failed_returns_static_only(self):
        s = SecurityScanner(client=MLXClient())
        with patch.object(
            s._client,
            "chat",
            new=AsyncMock(return_value={"status": "failed", "error": "timeout"}),
        ):
            result = await s.scan("x = 1", "python")
            assert result["status"] == "completed"
            assert result["total_findings"] == 0

    @pytest.mark.asyncio
    async def test_scan_llm_non_json_content(self):
        s = SecurityScanner(client=MLXClient())
        with patch.object(
            s._client,
            "chat",
            new=AsyncMock(return_value={"status": "completed", "content": "not a json array"}),
        ):
            result = await s.scan("x = 1", "python")
            assert result["status"] == "completed"
            assert result["total_findings"] == 0

    @pytest.mark.asyncio
    async def test_scan_with_static_findings_only(self):
        s = SecurityScanner()
        result = await s.scan("password = 'secret123'", "python")
        assert result["status"] == "completed"
        assert result["total_findings"] >= 1
        assert result["scan_mode"] == "static"

    # ── scan with fusion_security_url delegation ──

    @pytest.mark.asyncio
    async def test_scan_fusion_security_delegation_success(self):
        s = SecurityScanner(fusion_security_url="http://security:8080")
        delegated_findings = [
            {"type": "delegated_vuln", "severity": "high", "line": 1, "description": "from fusion-security"},
        ]
        with patch.object(
            s,
            "_delegate_scan",
            new=AsyncMock(return_value={"findings": delegated_findings}),
        ):
            result = await s.scan("code", "python")
            assert result["status"] == "completed"
            assert result["scan_mode"] == "static+fusion-security"
            assert result["total_findings"] >= 1
            types = {f["type"] for f in result["findings"]}
            assert "delegated_vuln" in types

    @pytest.mark.asyncio
    async def test_scan_fusion_security_delegation_fails_fallback_llm(self):
        s = SecurityScanner(fusion_security_url="http://security:8080")
        llm_fallback_findings = [
            {"type": "llm_fallback_vuln", "severity": "medium", "line": 1, "description": "from LLM fallback"},
        ]
        with patch.object(
            s,
            "_delegate_scan",
            new=AsyncMock(return_value={"findings": llm_fallback_findings}),
        ):
            result = await s.scan("code", "python")
            assert result["status"] == "completed"
            assert result["scan_mode"] == "static+fusion-security"
            types = {f["type"] for f in result["findings"]}
            assert "llm_fallback_vuln" in types

    @pytest.mark.asyncio
    async def test_delegate_scan_no_url(self):
        s = SecurityScanner()
        result = await s._delegate_scan("code", "python")
        assert result == {"findings": []}

    # ── fix ──

    @pytest.mark.asyncio
    async def test_fix_success(self):
        s = SecurityScanner(client=MLXClient())
        with patch.object(
            s._client,
            "chat",
            new=AsyncMock(return_value={"status": "completed", "content": "```\nsecure = True\n```"}),
        ):
            result = await s.fix("password = 'secret'", "hardcoded password")
            assert result["status"] == "completed"
            assert "fixed_code" in result
            assert "secure" in result["fixed_code"]

    @pytest.mark.asyncio
    async def test_fix_success_no_fence(self):
        s = SecurityScanner(client=MLXClient())
        with patch.object(
            s._client,
            "chat",
            new=AsyncMock(return_value={"status": "completed", "content": "secure = True"}),
        ):
            result = await s.fix("password = 'secret'", "hardcoded password")
            assert result["status"] == "completed"
            assert "secure" in result["fixed_code"]

    @pytest.mark.asyncio
    async def test_fix_failure(self):
        s = SecurityScanner(client=MLXClient())
        with patch.object(
            s._client,
            "chat",
            new=AsyncMock(return_value={"status": "failed", "error": "model unavailable"}),
        ):
            result = await s.fix("password = 'secret'", "hardcoded password")
            assert result["status"] == "failed"
            assert "error" in result

    # ── BoundaryType ──

    def test_boundary_type_values(self):
        assert BoundaryType.MICROSERVICE == "microservice"
        assert BoundaryType.MODULE == "module"
        assert BoundaryType.PACKAGE == "package"

    def test_boundary_type_all(self):
        assert BoundaryType.ALL == ("microservice", "module", "package")
        assert len(BoundaryType.ALL) == 3
