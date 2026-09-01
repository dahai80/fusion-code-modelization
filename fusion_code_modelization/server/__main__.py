from __future__ import annotations

import argparse
import logging

from ..core.config import DEFAULT_GATEWAY_URL
from .runner import DEFAULT_SERVER_PORT, run_server

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(prog="fusion-code-modelization-server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_SERVER_PORT)
    parser.add_argument("--mlx-url", default=DEFAULT_GATEWAY_URL)
    parser.add_argument("--allow-nonloopback", action="store_true")
    args = parser.parse_args()

    logger.info(
        "server CLI invoked: host=%s port=%d mlx=%s allow_nonloopback=%s",
        args.host,
        args.port,
        args.mlx_url,
        args.allow_nonloopback,
    )
    run_server(
        host=args.host,
        port=args.port,
        mlx_url=args.mlx_url,
        allow_nonloopback=args.allow_nonloopback,
    )


if __name__ == "__main__":
    main()
