# GateGuard: New file. Importers: pr_gen/__init__.py. Affected API: none (MicroserviceDecomposer+BoundaryType extracted from __init__.py). Data schemas: BoundaryType. User instruction: Phase 5 module structure cleanup.

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from fusion_code_modelization.core.client import MLXClient
from fusion_code_modelization.core.config import DEFAULT_GATEWAY_URL, ModelConfig

logger = logging.getLogger(__name__)


class BoundaryType:
    MICROSERVICE = "microservice"
    MODULE = "module"
    PACKAGE = "package"

    ALL = (MICROSERVICE, MODULE, PACKAGE)


class MicroserviceDecomposer:
    def __init__(self, mlx_url: str = DEFAULT_GATEWAY_URL, client: MLXClient | None = None):
        if client is not None:
            self._client = client
        else:
            config = ModelConfig(base_url=mlx_url)
            self._client = MLXClient(config)

    def analyze_boundaries(self, graph: dict, boundary_type: str = BoundaryType.MICROSERVICE) -> list[dict]:
        clusters = defaultdict(list)
        for node_id, _node in graph.get("nodes", {}).items():
            if boundary_type == BoundaryType.PACKAGE:
                parts = node_id.split("/")
                module = "/".join(parts[:1]) if parts else "root"
            elif boundary_type == BoundaryType.MODULE:
                parts = node_id.split("/")
                module = "/".join(parts[:2]) if len(parts) > 1 else parts[0] if parts else "root"
            else:
                module = node_id.split("/")[0] if "/" in node_id else "root"
            clusters[module].append(node_id)
        min_size = {"microservice": 2, "module": 1, "package": 1}.get(boundary_type, 2)
        services = []
        for module, files in clusters.items():
            if len(files) >= min_size:
                services.append(
                    {
                        "name": module,
                        "files": files,
                        "size": len(files),
                        "boundary_type": boundary_type,
                    }
                )
        logger.info("analyze_boundaries: type=%s found=%d", boundary_type, len(services))
        return services

    async def suggest_decomposition(
        self, code: str, language: str, boundary_type: str = BoundaryType.MICROSERVICE
    ) -> dict[str, Any]:
        boundary_desc = {
            BoundaryType.MICROSERVICE: "independent microservices with clear API boundaries",
            BoundaryType.MODULE: "logical modules within a monolith",
            BoundaryType.PACKAGE: "packages or namespaces for code organization",
        }.get(boundary_type, "microservices")
        result = await self._client.chat(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Analyze this {language} codebase and suggest how to split it into {boundary_desc}. "
                        f"Identify bounded contexts, boundaries, and API contracts.\n\n"
                        f"```{language}\n{code[:4000]}\n```"
                    ),
                }
            ],
            max_tokens=2048,
            temperature=0.1,
        )
        if result["status"] == "completed":
            return {"suggestions": result["content"], "language": language, "boundary_type": boundary_type}
        logger.warning("Decomposition suggestion failed: %s", result.get("error"))
        return {"error": result.get("error")}
