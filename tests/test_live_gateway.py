from __future__ import annotations

import os

import pytest

from fusion_code_modelization.core.client import MLXClient
from fusion_code_modelization.core.config import DEFAULT_GATEWAY_URL, ModelConfig

pytestmark = pytest.mark.live


def _gateway_reachable() -> bool:
    import httpx

    try:
        r = httpx.get(f"{DEFAULT_GATEWAY_URL.rstrip('/')}/models", timeout=3.0)
        return r.status_code == 200
    except Exception:
        return False


@pytest.fixture(autouse=True)
def _skip_if_gateway_down():
    if not _gateway_reachable():
        pytest.skip("fusion-gateway not reachable — start gateway + fusion-mlx upstream")


def test_gateway_lists_models():
    import httpx

    r = httpx.get(f"{DEFAULT_GATEWAY_URL.rstrip('/')}/models", timeout=5.0)
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 1


@pytest.mark.asyncio
async def test_gateway_chat_contract():
    api_key = os.environ.get("FUSION_MLX_API_KEY") or os.environ.get("MLX_API_KEY") or ""
    config = ModelConfig(base_url=DEFAULT_GATEWAY_URL)
    if api_key:
        config.api_key = api_key
    client = MLXClient(config)
    try:
        result = await client.chat(
            messages=[{"role": "user", "content": "Reply with exactly the word: pong"}],
            max_tokens=16,
            temperature=0.0,
        )
        assert result["status"] == "completed", f"chat failed: {result.get('error')}"
        assert isinstance(result.get("content"), str)
        assert result["content"].strip(), "empty content from gateway"
    finally:
        await client.aclose()
