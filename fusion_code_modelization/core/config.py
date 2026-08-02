from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum

logger = logging.getLogger(__name__)


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
    model: str = "qwen3.5-9b"
    temperature: float = 0.1
    max_tokens: int = 4096
    timeout: float = 120.0
    base_url: str = "http://localhost:11434/v1"
    retry_attempts: int = 2
    retry_delay: float = 1.0

    def to_chat_params(self) -> dict:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


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
    "code": ModelConfig(model="qwen3.5-9b", temperature=0.1, max_tokens=4096),
    "analysis": ModelConfig(model="qwen3.5-9b", temperature=0.0, max_tokens=2048),
    "creative": ModelConfig(model="qwen3.5-9b", temperature=0.3, max_tokens=4096),
    "fast": ModelConfig(model="qwen3.5-9b", temperature=0.1, max_tokens=1024, timeout=60.0),
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
