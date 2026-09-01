from __future__ import annotations

import os


def pytest_configure(config):
    # Strip API keys except for a live-only run (-m live), which needs the
    # real gateway key. The default addopts "-m 'not live'" must still strip
    # (so mocked tests never resolve a real key and enable auth by accident).
    markexpr = (config.option.markexpr or "").strip()
    is_live_only = markexpr == "live"
    if not is_live_only:
        for key in ("FUSION_SERVER_API_KEY", "FUSION_MLX_API_KEY", "MLX_API_KEY", "OPENAI_API_KEY"):
            os.environ.pop(key, None)
    os.environ.setdefault("FUSION_ALLOWED_HOSTS", "127.0.0.1,localhost,testserver")
