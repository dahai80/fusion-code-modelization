from __future__ import annotations

import os

import pytest

from fusion_code_modelization.core.client import MLXClient
from fusion_code_modelization.core.config import DEFAULT_GATEWAY_URL, ModelConfig

pytestmark = pytest.mark.live


def _api_key() -> str:
    return os.environ.get("FUSION_MLX_API_KEY") or os.environ.get("MLX_API_KEY") or ""


def _gateway_reachable() -> bool:
    import httpx

    try:
        headers = {"Authorization": f"Bearer {_api_key()}"} if _api_key() else {}
        r = httpx.get(f"{DEFAULT_GATEWAY_URL.rstrip('/')}/models", timeout=3.0, headers=headers)
        return r.status_code == 200
    except Exception:
        return False


@pytest.fixture(autouse=True)
def _skip_if_gateway_down():
    if not _gateway_reachable():
        pytest.skip("fusion-gateway not reachable — start gateway + fusion-mlx upstream")


def test_gateway_lists_models():
    import httpx

    headers = {"Authorization": f"Bearer {_api_key()}"} if _api_key() else {}
    r = httpx.get(f"{DEFAULT_GATEWAY_URL.rstrip('/')}/models", timeout=5.0, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 1


@pytest.mark.asyncio
async def test_gateway_chat_contract():
    api_key = os.environ.get("FUSION_MLX_API_KEY") or os.environ.get("MLX_API_KEY") or ""
    # Model id must be one the gateway's fusion-mlx upstream has loaded.
    # Override via env so CI can point at whatever the live upstream serves.
    model = os.environ.get("FUSION_LIVE_MODEL", "Qwen3.8-27B-4bit")
    config = ModelConfig(base_url=DEFAULT_GATEWAY_URL, model=model)
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
