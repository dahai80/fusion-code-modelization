"""Security scanner — scans legacy code for vulnerabilities, hardcoded secrets, and outdated deps."""
from __future__ import annotations

import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class SecurityScanner:
    """Scans legacy code for security issues and generates fixes."""

    def __init__(self, mlx_url: str = "http://localhost:11434/v1"):
        self.mlx_url = mlx_url.rstrip("/")

    async def scan(self, code: str, language: str) -> dict[str, Any]:
        """Scan code for security vulnerabilities."""
        findings = []

        # Static pattern checks
        findings.extend(self._check_hardcoded_secrets(code))
        findings.extend(self._check_vulnerable_patterns(code, language))

        # LLM-powered analysis
        llm_findings = await self._llm_scan(code, language)
        findings.extend(llm_findings.get("findings", []))

        return {
            "status": "completed",
            "total_findings": len(findings),
            "findings": findings,
            "language": language,
        }

    async def fix(self, code: str, vulnerability: str) -> dict[str, Any]:
        """Generate a fix for a detected vulnerability."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self.mlx_url}/chat/completions", json={
                    "model": "qwen3.5-9b",
                    "messages": [{
                        "role": "user",
                        "content": (
                            f"Fix this vulnerability: {vulnerability}\n\n"
                            f"```\n{code[:3000]}\n```\n\n"
                            f"Return only the fixed code, no explanation."
                        ),
                    }],
                    "max_tokens": 4096,
                    "temperature": 0.1,
                })
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                return {"status": "completed", "fixed_code": self._extract_code(content)}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def _llm_scan(self, code: str, language: str) -> dict[str, Any]:
        """Use LLM to identify security issues."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self.mlx_url}/chat/completions", json={
                    "model": "qwen3.5-9b",
                    "messages": [{
                        "role": "user",
                        "content": (
                            f"Scan this {language} code for security vulnerabilities. "
                            f"List: 1) SQL injection, 2) XSS, 3) hardcoded secrets, "
                            f"4) outdated crypto, 5) path traversal, 6) command injection. "
                            f"Return as JSON array: [{{'type': str, 'severity': 'high|medium|low', 'line': int, 'description': str}}]\n\n"
                            f"```{language}\n{code[:3000]}\n```"
                        ),
                    }],
                    "max_tokens": 1024,
                    "temperature": 0.1,
                })
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                import json
                if content.strip().startswith("["):
                    return {"findings": json.loads(content)}
        except Exception:
            pass
        return {"findings": []}

    @staticmethod
    def _check_hardcoded_secrets(code: str) -> list[dict]:
        findings = []
        patterns = [
            (r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"][^'\"]+['\"]", "Hardcoded password"),
            (r"(?i)(api_key|apikey|api-key)\s*[=:]\s*['\"][^'\"]+['\"]", "Hardcoded API key"),
            (r"(?i)(secret|token)\s*[=:]\s*['\"][^'\"]{8,}['\"]", "Hardcoded secret/token"),
            (r"(?i)-----BEGIN (RSA |EC )?PRIVATE KEY-----", "Embedded private key"),
        ]
        for i, line in enumerate(code.split("\n"), 1):
            for pattern, desc in patterns:
                if re.search(pattern, line):
                    findings.append({"type": "hardcoded_secret", "severity": "high", "line": i, "description": desc})
        return findings

    @staticmethod
    def _check_vulnerable_patterns(code: str, language: str) -> list[dict]:
        findings = []
        patterns = {
            "python": [(r"eval\s*\(", "Use of eval()"), (r"exec\s*\(", "Use of exec()"), (r"os\.system\s*\(", "Command injection risk")],
            "java": [(r"Runtime\.getRuntime\(\)\.exec", "Command injection risk"), (r"Statement\.executeQuery", "SQL injection risk")],
            "javascript": [(r"innerHTML\s*=", "XSS vulnerability"), (r"document\.write\s*\(", "XSS vulnerability")],
        }
        for i, line in enumerate(code.split("\n"), 1):
            for pattern, desc in patterns.get(language, []):
                if re.search(pattern, line):
                    findings.append({"type": "vulnerable_pattern", "severity": "medium", "line": i, "description": desc})
        return findings

    @staticmethod
    def _extract_code(content: str) -> str:
        import re
        match = re.search(r"```(?:\w+)?\n(.+?)\n```", content, re.DOTALL)
        return match.group(1).strip() if match else content.strip()