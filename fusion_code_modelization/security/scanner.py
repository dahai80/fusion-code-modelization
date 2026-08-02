from __future__ import annotations

import logging
import re
from typing import Any

from fusion_code_modelization.core.client import MLXClient
from fusion_code_modelization.core.config import ModelConfig

logger = logging.getLogger(__name__)


class SecurityScanner:
    def __init__(self, mlx_url: str = "http://localhost:11434/v1", client: MLXClient | None = None):
        if client is not None:
            self._client = client
        else:
            config = ModelConfig(base_url=mlx_url)
            self._client = MLXClient(config)

    async def scan(self, code: str, language: str) -> dict[str, Any]:
        findings = []
        findings.extend(self._check_hardcoded_secrets(code))
        findings.extend(self._check_vulnerable_patterns(code, language))
        llm_findings = await self._llm_scan(code, language)
        findings.extend(llm_findings.get("findings", []))
        return {
            "status": "completed",
            "total_findings": len(findings),
            "findings": findings,
            "language": language,
        }

    async def fix(self, code: str, vulnerability: str) -> dict[str, Any]:
        result = await self._client.chat(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Fix this vulnerability: {vulnerability}\n\n"
                        f"```\n{code[:3000]}\n```\n\n"
                        f"Return only the fixed code, no explanation."
                    ),
                }
            ],
            max_tokens=4096,
            temperature=0.1,
        )
        if result["status"] == "completed":
            return {"status": "completed", "fixed_code": MLXClient.extract_code(result["content"])}
        return {"status": "failed", "error": result.get("error", "Unknown")}

    async def _llm_scan(self, code: str, language: str) -> dict[str, Any]:
        result = await self._client.chat(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Scan this {language} code for security vulnerabilities. "
                        f"List: 1) SQL injection, 2) XSS, 3) hardcoded secrets, "
                        f"4) outdated crypto, 5) path traversal, 6) command injection. "
                        f"Return as JSON array: [{{'type': str, 'severity': 'high|medium|low', 'line': int, 'description': str}}]\n\n"
                        f"```{language}\n{code[:3000]}\n```"
                    ),
                }
            ],
            max_tokens=1024,
            temperature=0.1,
        )
        if result["status"] == "completed":
            import json

            content = result["content"]
            if content.strip().startswith("["):
                try:
                    return {"findings": json.loads(content)}
                except json.JSONDecodeError:
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
            "python": [
                (r"eval\s*\(", "Use of eval()"),
                (r"exec\s*\(", "Use of exec()"),
                (r"os\.system\s*\(", "Command injection risk"),
            ],
            "java": [
                (r"Runtime\.getRuntime\(\)\.exec", "Command injection risk"),
                (r"Statement\.executeQuery", "SQL injection risk"),
            ],
            "javascript": [(r"innerHTML\s*=", "XSS vulnerability"), (r"document\.write\s*\(", "XSS vulnerability")],
        }
        for i, line in enumerate(code.split("\n"), 1):
            for pattern, desc in patterns.get(language, []):
                if re.search(pattern, line):
                    findings.append(
                        {"type": "vulnerable_pattern", "severity": "medium", "line": i, "description": desc}
                    )
        return findings
