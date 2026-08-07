# GateGuard: New file. Importers: test runner. Affected API: DualStackClient, DualModelConfig, ModelRouter, ModelStack, RoutingStrategy. Data schemas: DualModelConfig(local_config, cloud_config, routing_strategy). User instruction: "开始阶段3"

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from fusion_code_modelization.core import (
    DEFAULT_LOCAL_MODEL,
    DualModelConfig,
    DualStackClient,
    ModelConfig,
    ModelRouter,
    ModelStack,
    RoutingStrategy,
)


class TestModelStack:
    def test_values(self):
        assert ModelStack.LOCAL.value == "local"
        assert ModelStack.CLOUD.value == "cloud"


class TestRoutingStrategy:
    def test_values(self):
        assert RoutingStrategy.LOCAL_FIRST.value == "local_first"
        assert RoutingStrategy.CLOUD_FIRST.value == "cloud_first"
        assert RoutingStrategy.COMPLEXITY_BASED.value == "complexity_based"
        assert RoutingStrategy.LOCAL_ONLY.value == "local_only"


class TestDualModelConfig:
    def test_defaults(self):
        cfg = DualModelConfig()
        assert cfg.routing_strategy == RoutingStrategy.LOCAL_FIRST
        assert cfg.complexity_threshold == 0.7
        assert cfg.fallback_enabled is True
        assert cfg.local_config.model == DEFAULT_LOCAL_MODEL
        assert cfg.cloud_config.model == "claude-sonnet-5"

    def test_get_config_local(self):
        cfg = DualModelConfig()
        c = cfg.get_config(ModelStack.LOCAL)
        assert c.model == DEFAULT_LOCAL_MODEL

    def test_get_config_cloud(self):
        cfg = DualModelConfig()
        c = cfg.get_config(ModelStack.CLOUD)
        assert c.model == "claude-sonnet-5"

    def test_custom_config(self):
        local = ModelConfig(model="my-local", base_url="http://l:11434/v1")
        cloud = ModelConfig(model="my-cloud", base_url="http://c:11434/v1")
        cfg = DualModelConfig(local_config=local, cloud_config=cloud, routing_strategy=RoutingStrategy.CLOUD_FIRST)
        assert cfg.get_config(ModelStack.LOCAL).model == "my-local"
        assert cfg.get_config(ModelStack.CLOUD).model == "my-cloud"


class TestModelRouter:
    def test_estimate_complexity_high(self):
        router = ModelRouter()
        score = router.estimate_complexity("Please refactor the architecture of this system")
        assert score >= 0.7

    def test_estimate_complexity_low(self):
        router = ModelRouter()
        score = router.estimate_complexity("format the code")
        assert score <= 0.2

    def test_estimate_complexity_none(self):
        router = ModelRouter()
        score = router.estimate_complexity("hello world")
        assert score == 0.0

    def test_route_local_first(self):
        cfg = DualModelConfig(routing_strategy=RoutingStrategy.LOCAL_FIRST)
        router = ModelRouter(cfg)
        assert router.route("any prompt") == ModelStack.LOCAL

    def test_route_cloud_first(self):
        cfg = DualModelConfig(routing_strategy=RoutingStrategy.CLOUD_FIRST)
        router = ModelRouter(cfg)
        assert router.route("any prompt") == ModelStack.CLOUD

    def test_route_local_only(self):
        cfg = DualModelConfig(routing_strategy=RoutingStrategy.LOCAL_ONLY)
        router = ModelRouter(cfg)
        assert router.route("complex architecture refactor") == ModelStack.LOCAL

    def test_route_complexity_based_high(self):
        cfg = DualModelConfig(routing_strategy=RoutingStrategy.COMPLEXITY_BASED, complexity_threshold=0.5)
        router = ModelRouter(cfg)
        assert router.route("redesign the architecture") == ModelStack.CLOUD

    def test_route_complexity_based_low(self):
        cfg = DualModelConfig(routing_strategy=RoutingStrategy.COMPLEXITY_BASED, complexity_threshold=0.5)
        router = ModelRouter(cfg)
        assert router.route("lint the code") == ModelStack.LOCAL

    def test_get_config_for_prompt(self):
        cfg = DualModelConfig(routing_strategy=RoutingStrategy.LOCAL_FIRST)
        router = ModelRouter(cfg)
        config = router.get_config_for_prompt("hello")
        assert config.model == DEFAULT_LOCAL_MODEL


class TestDualStackClient:
    def test_init_default(self):
        client = DualStackClient()
        assert client.active_stack == "local"

    def test_switch_stack(self):
        client = DualStackClient()
        client.switch_stack("cloud")
        assert client.active_stack == "cloud"
        client.switch_stack("local")
        assert client.active_stack == "local"

    def test_switch_stack_invalid(self):
        client = DualStackClient()
        with pytest.raises(ValueError):
            client.switch_stack("invalid")

    def test_get_client_local(self):
        client = DualStackClient()
        c = client._get_client("local")
        assert c.config.model == DEFAULT_LOCAL_MODEL

    def test_get_client_cloud(self):
        client = DualStackClient()
        c = client._get_client("cloud")
        assert c.config.model == "claude-sonnet-5"

    @pytest.mark.asyncio
    async def test_smart_chat_local_first(self):
        client = DualStackClient()
        with patch.object(
            client._local_client, "chat", new=AsyncMock(return_value={"status": "completed", "content": "ok"})
        ):
            result = await client.smart_chat(messages=[{"role": "user", "content": "simple test"}])
            assert result["status"] == "completed"
            assert result["routed_stack"] == "local"

    @pytest.mark.asyncio
    async def test_smart_chat_fallback(self):
        cfg = DualModelConfig(routing_strategy=RoutingStrategy.LOCAL_FIRST, fallback_enabled=True)
        client = DualStackClient(cfg)
        with (
            patch.object(
                client._local_client, "chat", new=AsyncMock(return_value={"status": "failed", "error": "down"})
            ),
            patch.object(
                client._cloud_client, "chat", new=AsyncMock(return_value={"status": "completed", "content": "cloud ok"})
            ),
        ):
            result = await client.smart_chat(messages=[{"role": "user", "content": "test"}])
            assert result["status"] == "completed"
            assert result["routed_stack"] == "cloud"

    @pytest.mark.asyncio
    async def test_smart_chat_no_fallback(self):
        cfg = DualModelConfig(routing_strategy=RoutingStrategy.LOCAL_FIRST, fallback_enabled=False)
        client = DualStackClient(cfg)
        with patch.object(
            client._local_client, "chat", new=AsyncMock(return_value={"status": "failed", "error": "down"})
        ):
            result = await client.smart_chat(messages=[{"role": "user", "content": "test"}])
            assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_smart_chat_complexity_routing(self):
        cfg = DualModelConfig(routing_strategy=RoutingStrategy.COMPLEXITY_BASED, complexity_threshold=0.5)
        client = DualStackClient(cfg)
        with patch.object(
            client._cloud_client, "chat", new=AsyncMock(return_value={"status": "completed", "content": "arch ok"})
        ):
            result = await client.smart_chat(messages=[{"role": "user", "content": "redesign the architecture"}])
            assert result["status"] == "completed"
            assert result["routed_stack"] == "cloud"
