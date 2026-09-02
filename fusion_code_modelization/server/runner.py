from __future__ import annotations

import logging
import os
import socket

from ..core.config import DEFAULT_GATEWAY_URL, DEFAULT_SERVER_PORT
from .app import create_app

logger = logging.getLogger(__name__)

_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1", "0:0:0:0:0:0:0:1"}


def _is_loopback(host: str) -> bool:
    if host in _LOOPBACK_HOSTS:
        return True
    try:
        return socket.gethostbyname(host).startswith("127.")
    except OSError:
        return False


def _configure_logging() -> None:
    level_name = os.environ.get("FUSION_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("logging configured level=%s", level_name)


def run_server(
    host: str = "127.0.0.1",
    port: int = DEFAULT_SERVER_PORT,
    mlx_url: str = DEFAULT_GATEWAY_URL,
    allow_nonloopback: bool = False,
) -> None:
    import uvicorn

    _configure_logging()
    if not allow_nonloopback and not _is_loopback(host):
        logger.error("refusing non-loopback host %s (use allow_nonloopback=True to override)", host)
        raise ValueError(f"non-loopback host '{host}' rejected; bind to 127.0.0.1 or pass allow_nonloopback=True")
    app = create_app(mlx_url=mlx_url)
    logger.info("Starting REST API on %s:%d (mlx=%s)", host, port, mlx_url)
    uvicorn.run(app, host=host, port=port, log_level="info")
