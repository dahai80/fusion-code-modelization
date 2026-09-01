from __future__ import annotations

import os


def pytest_configure(config):
    # Strip API keys only for non-live runs so mocked tests never leak real
    # keys into clients. Live runs (-m live) need the real gateway key.
    if not config.option.markexpr or "live" not in config.option.markexpr:
        for key in ("FUSION_SERVER_API_KEY", "FUSION_MLX_API_KEY", "MLX_API_KEY", "OPENAI_API_KEY"):
            os.environ.pop(key, None)
    os.environ.setdefault("FUSION_ALLOWED_HOSTS", "127.0.0.1,localhost,testserver")
