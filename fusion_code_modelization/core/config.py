from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import StrEnum

logger = logging.getLogger(__name__)

DEFAULT_LOCAL_MODEL = "Qwen3.5-9B-4bit"
DEFAULT_GATEWAY_URL = "http://localhost:11432/v1"
GATEWAY_PORT = 11432
DEFAULT_SERVER_PORT = 11459


def _resolve_api_key() -> str:
    for env_name in ("FUSION_MLX_API_KEY", "MLX_API_KEY", "OPENAI_API_KEY"):
        key = os.environ.get(env_name, "")
        if key:
            return key
    logger.warning(
        "No API key found in FUSION_MLX_API_KEY/MLX_API_KEY/OPENAI_API_KEY; "
        "set FUSION_MLX_API_KEY to the fusion-gateway client key"
    )
    return ""


class ModelStack(StrEnum):
    LOCAL = "local"
    CLOUD = "cloud"


class RoutingStrategy(StrEnum):
    LOCAL_FIRST = "local_first"
    CLOUD_FIRST = "cloud_first"
    COMPLEXITY_BASED = "complexity_based"
    LOCAL_ONLY = "local_only"


@dataclass
class ModelConfig:
    model: str = DEFAULT_LOCAL_MODEL
    temperature: float = 0.1
    max_tokens: int = 4096
    timeout: float = 120.0
    base_url: str = DEFAULT_GATEWAY_URL
    retry_attempts: int = 2
    retry_delay: float = 1.0
    api_key: str = field(default_factory=_resolve_api_key)

    def to_chat_params(self) -> dict:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

    def auth_headers(self) -> dict[str, str]:
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}


@dataclass
class DualModelConfig:
    local_config: ModelConfig = field(default_factory=ModelConfig)
    cloud_config: ModelConfig = field(
        default_factory=lambda: ModelConfig(
            model="claude-sonnet-5",
            base_url="https://api.anthropic.com/v1",
            timeout=60.0,
        )
    )
    routing_strategy: RoutingStrategy = RoutingStrategy.LOCAL_FIRST
    complexity_threshold: float = 0.7
    fallback_enabled: bool = True

    def get_config(self, stack: ModelStack) -> ModelConfig:
        if stack == ModelStack.CLOUD:
            return self.cloud_config
        return self.local_config


MODEL_PRESETS: dict[str, ModelConfig] = {
    "default": ModelConfig(),
    "code": ModelConfig(model=DEFAULT_LOCAL_MODEL, temperature=0.1, max_tokens=4096),
    "analysis": ModelConfig(model=DEFAULT_LOCAL_MODEL, temperature=0.0, max_tokens=2048),
    "creative": ModelConfig(model=DEFAULT_LOCAL_MODEL, temperature=0.3, max_tokens=4096),
    "fast": ModelConfig(model=DEFAULT_LOCAL_MODEL, temperature=0.1, max_tokens=1024, timeout=60.0),
}


def get_model_config(preset: str = "default") -> ModelConfig:
    if preset in MODEL_PRESETS:
        return ModelConfig(**{k: v for k, v in MODEL_PRESETS[preset].__dict__.items()})
    logger.warning("Unknown preset '%s', using default", preset)
    return ModelConfig()


class ModelRouter:
    COMPLEXITY_KEYWORDS: dict[str, float] = {
        "architecture": 0.9,
        "refactor": 0.7,
        "migrate": 0.8,
        "redesign": 0.9,
        "debug": 0.6,
        "fix": 0.4,
        "test": 0.3,
        "format": 0.1,
        "lint": 0.2,
        "document": 0.3,
        "explain": 0.4,
        "transpile": 0.7,
        "security": 0.6,
        "scan": 0.5,
        "decompose": 0.8,
    }

    def __init__(self, dual_config: DualModelConfig | None = None):
        self.dual_config = dual_config or DualModelConfig()

    def estimate_complexity(self, prompt: str) -> float:
        prompt_lower = prompt.lower()
        max_score = 0.0
        for keyword, score in self.COMPLEXITY_KEYWORDS.items():
            if keyword in prompt_lower:
                max_score = max(max_score, score)
        return max_score

    def route(self, prompt: str) -> ModelStack:
        strategy = self.dual_config.routing_strategy
        if strategy == RoutingStrategy.LOCAL_ONLY:
            return ModelStack.LOCAL
        if strategy == RoutingStrategy.LOCAL_FIRST:
            return ModelStack.LOCAL
        if strategy == RoutingStrategy.CLOUD_FIRST:
            return ModelStack.CLOUD
        if strategy == RoutingStrategy.COMPLEXITY_BASED:
            complexity = self.estimate_complexity(prompt)
            if complexity >= self.dual_config.complexity_threshold:
                return ModelStack.CLOUD
            return ModelStack.LOCAL
        return ModelStack.LOCAL

    def get_config_for_prompt(self, prompt: str) -> ModelConfig:
        stack = self.route(prompt)
        return self.dual_config.get_config(stack)


class OfflineMode(StrEnum):
    FULL_OFFLINE = "full_offline"
    SEMI_OFFLINE = "semi_offline"
    ONLINE = "online"


@dataclass
class OfflineConfig:
    mode: OfflineMode = OfflineMode.ONLINE
    local_model_ids: list[str] = field(default_factory=lambda: [DEFAULT_LOCAL_MODEL])
    cloud_fallback_enabled: bool = True
    cache_dir: str = ".fusion/offline_cache"
    max_cache_size_mb: float = 5000.0
    auto_detect_mode: bool = True
    preload_models: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "mode": self.mode.value,
            "local_model_ids": self.local_model_ids,
            "cloud_fallback_enabled": self.cloud_fallback_enabled,
            "cache_dir": self.cache_dir,
            "max_cache_size_mb": self.max_cache_size_mb,
            "auto_detect_mode": self.auto_detect_mode,
            "preload_models": self.preload_models,
        }

    @classmethod
    def from_dict(cls, data: dict) -> OfflineConfig:
        return cls(
            mode=OfflineMode(data.get("mode", "online")),
            local_model_ids=data.get("local_model_ids", [DEFAULT_LOCAL_MODEL]),
            cloud_fallback_enabled=data.get("cloud_fallback_enabled", True),
            cache_dir=data.get("cache_dir", ".fusion/offline_cache"),
            max_cache_size_mb=data.get("max_cache_size_mb", 5000.0),
            auto_detect_mode=data.get("auto_detect_mode", True),
            preload_models=data.get("preload_models", []),
        )
