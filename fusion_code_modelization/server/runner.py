from __future__ import annotations

import logging

from .app import create_app

logger = logging.getLogger(__name__)


def run_server(
    host: str = "127.0.0.1",
    port: int = 11441,
    mlx_url: str = "http://localhost:11434/v1",
) -> None:
    import uvicorn

    app = create_app(mlx_url=mlx_url)
    logger.info("Starting REST API on %s:%d (mlx=%s)", host, port, mlx_url)
    uvicorn.run(app, host=host, port=port, log_level="info")
