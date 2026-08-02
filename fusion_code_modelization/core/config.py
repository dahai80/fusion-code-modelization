from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


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
