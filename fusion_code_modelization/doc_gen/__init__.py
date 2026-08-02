from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ..core.client import MLXClient

logger = logging.getLogger(__name__)


@dataclass
class DocSection:
    title: str
    content: str = ""
    order: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title, "content": self.content, "order": self.order}


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
