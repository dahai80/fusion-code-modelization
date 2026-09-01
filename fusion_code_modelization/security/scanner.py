# GateGuard: Importers: security/__init__.py, CLI. Affected API: adds scan_stream(). Data schemas: none. User instruction: Phase 6 — add streaming LLM support.

from __future__ import annotations

import contextlib
import json
import logging
import re
from collections.abc import AsyncIterator
from typing import Any

import httpx

from fusion_code_modelization.core.client import MLXClient
from fusion_code_modelization.core.config import DEFAULT_GATEWAY_URL, ModelConfig

logger = logging.getLogger(__name__)

_LARGE_INPUT_WARN = 64_000


class SecurityScanner:
    def __init__(
        self,
        mlx_url: str = DEFAULT_GATEWAY_URL,
        client: MLXClient | None = None,
        fusion_security_url: str | None = None,
        static_only: bool | None = None,
    ):
        if client is not None:
            self._client = client
        else:
            config = ModelConfig(base_url=mlx_url)
            self._client = MLXClient(config)
        self._fusion_security_url = fusion_security_url
        if static_only is not None:
            self._static_only = static_only
        else:
            self._static_only = fusion_security_url is None and client is None

    async def scan(self, code: str, language: str) -> dict[str, Any]:
        findings = []
        findings.extend(self._check_hardcoded_secrets(code))
        findings.extend(self._check_vulnerable_patterns(code, language))

        if self._fusion_security_url:
            delegated = await self._delegate_scan(code, language)
            findings.extend(delegated.get("findings", []))
        elif not self._static_only:
            llm_findings = await self._llm_scan(code, language)
            findings.extend(llm_findings.get("findings", []))

        return {
            "status": "completed",
            "total_findings": len(findings),
            "findings": findings,
            "language": language,
            "scan_mode": "static+fusion-security"
            if self._fusion_security_url
            else ("static+llm" if not self._static_only else "static"),
        }

    async def scan_stream(self, code: str, language: str) -> AsyncIterator[dict[str, Any]]:
        if len(code) > _LARGE_INPUT_WARN:
            logger.warning("scan_stream large input: %d chars (no truncation; full code sent to LLM)", len(code))
        static_findings = []
        static_findings.extend(self._check_hardcoded_secrets(code))
        static_findings.extend(self._check_vulnerable_patterns(code, language))
        yield {"type": "findings", "findings": static_findings, "phase": "static"}

        if self._static_only:
            yield {
                "type": "done",
                "result": {
                    "status": "completed",
                    "total_findings": len(static_findings),
                    "findings": static_findings,
                    "language": language,
                    "scan_mode": "static",
                },
            }
            return

        if self._fusion_security_url:
            try:
                async with httpx.AsyncClient(timeout=30.0) as http:
                    resp = await http.post(
                        f"{self._fusion_security_url}/api/v1/scan",
                        json={"code": code, "language": language},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    delegated_findings = data.get("findings", [])
                    all_findings = static_findings + delegated_findings
                    yield {"type": "findings", "findings": delegated_findings, "phase": "delegated"}
                    yield {
                        "type": "done",
                        "result": {
                            "status": "completed",
                            "total_findings": len(all_findings),
                            "findings": all_findings,
                            "language": language,
                            "scan_mode": "static+fusion-security",
                        },
                    }
                    return
            except (httpx.HTTPError, json.JSONDecodeError) as e:
                logger.warning("fusion-security delegation failed in stream: %s", e)

        prompt = (
            f"Scan this {language} code for security vulnerabilities. "
            f"List: 1) SQL injection, 2) XSS, 3) hardcoded secrets, "
            f"4) outdated crypto, 5) path traversal, 6) command injection. "
            f"Return as JSON array: [{{'type': str, 'severity': 'high|medium|low', 'line': int, 'description': str}}]\n\n"
            f"```{language}\n{code}\n```"
        )
        accumulated = []
        try:
            async for token in self._client.chat_stream(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.1,
            ):
                accumulated.append(token)
                yield {"type": "token", "content": token}

            full = "".join(accumulated)
            llm_findings = []
            if full.strip().startswith("["):
                parsed = None
                with contextlib.suppress(json.JSONDecodeError):
                    parsed = json.loads(full)
                if isinstance(parsed, list):
                    llm_findings = self._validate_findings(parsed)
                    dropped = len(parsed) - len(llm_findings)
                    if dropped:
                        logger.warning("dropped %d malformed LLM finding(s)", dropped)
            all_findings = static_findings + llm_findings
            yield {
                "type": "done",
                "result": {
                    "status": "completed",
                    "total_findings": len(all_findings),
                    "findings": all_findings,
                    "language": language,
                    "scan_mode": "static+llm",
                },
            }
        except Exception as e:
            logger.error("scan_stream LLM failed: %s", e)
            yield {
                "type": "done",
                "result": {
                    "status": "completed",
                    "total_findings": len(static_findings),
                    "findings": static_findings,
                    "language": language,
                    "scan_mode": "static",
                    "llm_error": str(e),
                },
            }

    async def fix(self, code: str, vulnerability: str) -> dict[str, Any]:
        result = await self._client.chat(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Fix this vulnerability: {vulnerability}\n\n"
                        f"```\n{code}\n```\n\n"
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

    def scan_static(self, code: str, language: str) -> dict[str, Any]:
        findings = []
        findings.extend(self._check_hardcoded_secrets(code))
        findings.extend(self._check_vulnerable_patterns(code, language))
        return {
            "status": "completed",
            "total_findings": len(findings),
            "findings": findings,
            "language": language,
            "scan_mode": "static",
        }

    async def _delegate_scan(self, code: str, language: str) -> dict[str, Any]:
        if not self._fusion_security_url:
            return {"findings": []}
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                resp = await http.post(
                    f"{self._fusion_security_url}/api/v1/scan",
                    json={"code": code, "language": language},
                )
                resp.raise_for_status()
                data = resp.json()
                logger.info("fusion-security delegated scan returned %d findings", len(data.get("findings", [])))
                return data
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            logger.warning("fusion-security delegation failed, falling back to LLM: %s", e)
            llm_findings = await self._llm_scan(code, language)
            return llm_findings

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
                        f"```{language}\n{code}\n```"
                    ),
                }
            ],
            max_tokens=1024,
            temperature=0.1,
        )
        if result["status"] == "completed":
            content = result["content"]
            if content.strip().startswith("["):
                try:
                    parsed = json.loads(content)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, list):
                    return {"findings": self._validate_findings(parsed)}
        return {"findings": []}

    @staticmethod
    def _validate_findings(raw: list) -> list[dict]:
        valid = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            sev = str(item.get("severity", "low")).lower()
            if sev not in ("high", "medium", "low"):
                sev = "low"
            finding = {
                "type": str(item.get("type", "unknown")),
                "severity": sev,
                "line": item.get("line", 0) if isinstance(item.get("line"), int) else 0,
                "description": str(item.get("description", "")),
            }
            valid.append(finding)
        return valid

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
            "javascript": [
                (r"innerHTML\s*=", "XSS vulnerability"),
                (r"document\.write\s*\(", "XSS vulnerability"),
            ],
        }
        for i, line in enumerate(code.split("\n"), 1):
            for pattern, desc in patterns.get(language, []):
                if re.search(pattern, line):
                    findings.append(
                        {"type": "vulnerable_pattern", "severity": "medium", "line": i, "description": desc}
                    )
        return findings
