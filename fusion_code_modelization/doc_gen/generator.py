# GateGuard: Importers: doc_gen/__init__.py, CLI. Affected API: adds generate_docs_stream(). Data schemas: none. User instruction: Phase 6 — add streaming LLM support.

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from ..core.client import MLXClient
from .models import DocSection

logger = logging.getLogger(__name__)


DOC_PROMPT = """Generate comprehensive documentation for the following code.

Documentation type: {doc_type}
Language: {language}

Code:
```{language}
{code}
```

Requirements:
- Clear module-level overview
- Function/class descriptions with parameter docs
- Usage examples where appropriate
- Return value descriptions

Generate the documentation:"""


API_DOC_PROMPT = """Generate API documentation for the following code.

Language: {language}

Code:
```{language}
{code}
```

Produce:
1. Endpoint/method signatures
2. Request/response schemas
3. Error codes
4. Usage examples

Return the API documentation:"""


class DocumentationGenerator:
    def __init__(self, mlx_url: str = "http://localhost:11434/v1", client: MLXClient | None = None):
        from ..core.config import ModelConfig

        self._client = client or MLXClient(config=ModelConfig(base_url=mlx_url))

    async def generate_docs(self, code: str, language: str, doc_type: str = "module") -> dict[str, Any]:
        logger.info("Generating %s docs for %s code (%d chars)", doc_type, language, len(code))
        prompt = DOC_PROMPT.format(doc_type=doc_type, language=language, code=code[:6000])
        try:
            response = await self._client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            docs = response.get("content", "")
            if docs:
                docs = self._client.extract_code(docs)
            return {"status": "completed", "documentation": docs, "doc_type": doc_type, "language": language}
        except Exception as e:
            logger.error("Doc generation failed: %s", e)
            return {"status": "failed", "error": str(e)}

    async def generate_docs_stream(
        self, code: str, language: str, doc_type: str = "module"
    ) -> AsyncIterator[dict[str, Any]]:
        logger.info("Streaming %s docs for %s code (%d chars)", doc_type, language, len(code))
        prompt = DOC_PROMPT.format(doc_type=doc_type, language=language, code=code[:6000])
        accumulated = []
        try:
            async for token in self._client.chat_stream(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            ):
                accumulated.append(token)
                yield {"type": "token", "content": token}

            full = "".join(accumulated)
            docs = self._client.extract_code(full)
            yield {
                "type": "done",
                "result": {
                    "status": "completed",
                    "documentation": docs,
                    "doc_type": doc_type,
                    "language": language,
                },
            }
        except Exception as e:
            logger.error("generate_docs_stream failed: %s", e)
            yield {"type": "done", "result": {"status": "failed", "error": str(e)}}

    async def generate_api_docs(self, code: str, language: str) -> dict[str, Any]:
        logger.info("Generating API docs for %s code (%d chars)", language, len(code))
        prompt = API_DOC_PROMPT.format(language=language, code=code[:6000])
        try:
            response = await self._client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            docs = response.get("content", "")
            if docs:
                docs = self._client.extract_code(docs)
            return {"status": "completed", "documentation": docs, "doc_type": "api", "language": language}
        except Exception as e:
            logger.error("API doc generation failed: %s", e)
            return {"status": "failed", "error": str(e)}

    @staticmethod
    def build_readme(sections: list[DocSection]) -> str:
        parts = []
        for s in sorted(sections, key=lambda x: x.order):
            parts.append(f"## {s.title}\n\n{s.content}")
        return "\n\n---\n\n".join(parts)
