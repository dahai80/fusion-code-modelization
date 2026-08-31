from __future__ import annotations

import logging

from ..core.config import DEFAULT_GATEWAY_URL, DEFAULT_SERVER_PORT
from .app import create_app

logger = logging.getLogger(__name__)


def run_server(
    host: str = "127.0.0.1",
    port: int = DEFAULT_SERVER_PORT,
    mlx_url: str = DEFAULT_GATEWAY_URL,
) -> None:
    import uvicorn

    app = create_app(mlx_url=mlx_url)
    logger.info("Starting REST API on %s:%d (mlx=%s)", host, port, mlx_url)
    uvicorn.run(app, host=host, port=port, log_level="info")
