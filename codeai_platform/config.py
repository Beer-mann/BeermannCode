"""
Configuration module for CodeAI Platform.
Manages AI model settings, Ollama integration, multi-tier routing, and external providers.
"""

from typing import Dict, Optional, List
from dataclasses import dataclass, field
import json
import os
from pathlib import Path


# All available Ollama models on 192.168.0.213
OLLAMA_MODELS = {
    # Code specialists
    "qwen2.5-coder:7b": {"size": "7.6B", "type": "code", "vram_gb": 4.7, "speed": "medium", "tier": 1},
    "deepseek-coder:6.7b": {"size": "7B", "type": "code", "vram_gb": 3.8, "speed": "medium", "tier": 1},
    "codeqwen:7b": {"size": "7.3B", "type": "code", "vram_gb": 4.2, "speed": "medium", "tier": 1},
    # General purpose
    "mistral:7b-instruct": {"size": "7.2B", "type": "general", "vram_gb": 4.4, "speed": "medium", "tier": 1},
    "mistral:7b-instruct-q4_K_M": {"size": "7B", "type": "general", "vram_gb": 4.4, "speed": "medium", "tier": 1},
    "neural-chat:7b-v3.1-q4_K_M": {"size": "7B", "type": "chat", "vram_gb": 4.4, "speed": "medium", "tier": 1},
    "llama3.1:latest": {"size": "8B", "type": "general", "vram_gb": 4.9, "speed": "medium", "tier": 1},
    "llama3.2:latest": {"size": "3.2B", "type": "general", "vram_gb": 2.0, "speed": "fast", "tier": 1},
    "gemma3:4b": {"size": "4.3B", "type": "general", "vram_gb": 3.3, "speed": "fast", "tier": 1},
    # Small/fast
    "phi:2.7b": {"size": "3B", "type": "fast", "vram_gb": 1.6, "speed": "fast", "tier": 1},
    "dolphin-phi:latest": {"size": "3B", "type": "fast", "vram_gb": 1.6, "speed": "fast", "tier": 1},
}

# External provider models (Tier 2-4)
EXTERNAL_MODELS = {
    # Tier 2: Codex (OpenAI) — moderate cost
    "codex": {"provider": "openai", "model": "gpt-4.1-mini", "tier": 2, "cost": "low", "type": "code"},
    "codex-full": {"provider": "openai", "model": "gpt-4.1", "tier": 3, "cost": "medium", "type": "code"},
    # Tier 3: Claude (Anthropic via OpenClaw)
    "claude-haiku": {"provider": "openclaw", "model": "anthropic/claude-haiku-4-5", "tier": 2, "cost": "low", "type": "general"},
    "claude-sonnet": {"provider": "openclaw", "model": "anthropic/claude-sonnet-4-6", "tier": 3, "cost": "medium", "type": "code"},
    "claude-opus": {"provider": "openclaw", "model": "anthropic/claude-opus-4-6", "tier": 4, "cost": "high", "type": "code"},
}

# Task-to-model routing (Tier 1 = Ollama, free)
MODEL_ROUTING = {
    "code_generation": ["qwen2.5-coder:7b", "deepseek-coder:6.7b", "codeqwen:7b"],
    "code_review": ["qwen2.5-coder:7b", "deepseek-coder:6.7b", "mistral:7b-instruct"],
    "code_analysis": ["qwen2.5-coder:7b", "codeqwen:7b", "mistral:7b-instruct"],
    "refactor": ["qwen2.5-coder:7b", "deepseek-coder:6.7b", "codeqwen:7b"],
    "general": ["mistral:7b-instruct", "llama3.1:latest", "neural-chat:7b-v3.1-q4_K_M"],
    "quick": ["phi:2.7b", "dolphin-phi:latest", "llama3.2:latest", "gemma3:4b"],
    "chat": ["neural-chat:7b-v3.1-q4_K_M", "llama3.2:latest", "gemma3:4b"],
    "test_generation": ["qwen2.5-coder:7b", "deepseek-coder:6.7b", "codeqwen:7b"],
    "security_scan": ["qwen2.5-coder:7b", "mistral:7b-instruct", "llama3.1:latest"],
    "documentation": ["mistral:7b-instruct", "llama3.1:latest", "gemma3:4b"],
}


@dataclass
class CodeAIConfig:
    """Configuration for CodeAI Platform."""

    project_name: str = "default_project"
    project_type: str = "general"
    supported_languages: List[str] = field(default_factory=lambda: [
        "python", "javascript", "typescript", "bash", "java", "cpp", "go", "rust", "csharp"
    ])

    # Ollama settings
    ollama_host: str = "http://192.168.0.213:11434"
    ollama_models: Dict = field(default_factory=lambda: dict(OLLAMA_MODELS))
    model_routing: Dict = field(default_factory=lambda: dict(MODEL_ROUTING))

    # External providers
    external_models: Dict = field(default_factory=lambda: dict(EXTERNAL_MODELS))
    enable_external: bool = False  # Must be explicitly enabled by user
    max_tier: int = 1  # 1=Ollama only, 2=+cheap external, 3=+medium, 4=+expensive

    # Default models per task
    default_code_model: str = "qwen2.5-coder:7b"
    default_review_model: str = "qwen2.5-coder:7b"
    default_general_model: str = "mistral:7b-instruct"
    default_fast_model: str = "phi:2.7b"
    fallback_model: str = "dolphin-phi:latest"

    # OpenAI-compatible API (points to Ollama)
    openai_base_url: str = "http://192.168.0.213:11434/v1"
    openai_api_key: str = "ollama-local"
    openai_model: str = "qwen2.5-coder:7b"

    # Real OpenAI (for Codex tier)
    openai_real_api_key: str = ""

    max_tokens: int = 4096
    temperature: float = 0.2

    # Feature flags
    enable_code_analysis: bool = True
    enable_code_generation: bool = True
    enable_code_review: bool = True
    enable_refactoring: bool = True
    enable_test_runner: bool = True
    enable_dependency_scan: bool = True
    enable_security_scan: bool = True
    enable_health_monitor: bool = True

    # Review settings
    review_depth: str = "standard"
    auto_fix_issues: bool = False

    # Generation settings
    generation_style: str = "clean"
    include_comments: bool = True
    include_tests: bool = True

    # Alert settings
    alert_on_ollama_down: bool = True
    alert_channel: str = "whatsapp"

    def get_model_for_task(self, task: str, min_tier: int = 1) -> str:
        """Get the best model for a given task type, respecting tier limits."""
        models = self.model_routing.get(task, self.model_routing.get("general", []))
        if models:
            return models[0]
        return self.fallback_model

    def get_external_model(self, task: str, tier: int = 2) -> Optional[Dict]:
        """Get an external model for fallback, if enabled and tier allows."""
        if not self.enable_external or tier > self.max_tier:
            return None
        candidates = {k: v for k, v in self.external_models.items() if v["tier"] <= tier}
        # Prefer code models for code tasks
        code_tasks = {"code_generation", "code_review", "refactor", "test_generation"}
        if task in code_tasks:
            for name, info in candidates.items():
                if info["type"] == "code":
                    return {"name": name, **info}
        # Return cheapest available
        if candidates:
            cheapest = min(candidates.items(), key=lambda x: x[1]["tier"])
            return {"name": cheapest[0], **cheapest[1]}
        return None

    def get_openai_client(self, use_real: bool = False):
        """Create an OpenAI client. use_real=True for actual OpenAI API."""
        try:
            from openai import OpenAI
            if use_real and self.openai_real_api_key:
                return OpenAI(api_key=self.openai_real_api_key)
            return OpenAI(
                base_url=self.openai_base_url,
                api_key=self.openai_api_key,
            )
        except ImportError:
            return None

    def to_dict(self) -> Dict:
        """Convert configuration to dictionary."""
        return {
            "project_name": self.project_name,
            "project_type": self.project_type,
            "supported_languages": self.supported_languages,
            "ollama_host": self.ollama_host,
            "default_code_model": self.default_code_model,
            "default_review_model": self.default_review_model,
            "default_general_model": self.default_general_model,
            "default_fast_model": self.default_fast_model,
            "fallback_model": self.fallback_model,
            "enable_external": self.enable_external,
            "max_tier": self.max_tier,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "enable_code_analysis": self.enable_code_analysis,
            "enable_code_generation": self.enable_code_generation,
            "enable_code_review": self.enable_code_review,
            "enable_refactoring": self.enable_refactoring,
            "enable_test_runner": self.enable_test_runner,
            "enable_dependency_scan": self.enable_dependency_scan,
            "enable_security_scan": self.enable_security_scan,
            "enable_health_monitor": self.enable_health_monitor,
            "available_ollama_models": list(self.ollama_models.keys()),
            "available_external_models": list(self.external_models.keys()),
        }

    @classmethod
    def from_file(cls, config_path: str = "config.json") -> "CodeAIConfig":
        """Load configuration from JSON file."""
        path = Path(config_path)
        if not path.exists():
            return cls()
        with open(path) as f:
            data = json.load(f)
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        # Auto-detect real OpenAI key from env
        if not filtered.get("openai_real_api_key"):
            env_key = os.environ.get("OPENAI_API_KEY", "")
            if env_key and not env_key.startswith("ollama"):
                filtered["openai_real_api_key"] = env_key
        return cls(**filtered)

    @classmethod
    def from_dict(cls, config_dict: Dict) -> "CodeAIConfig":
        """Create configuration from dictionary."""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in config_dict.items() if k in valid_fields}
        return cls(**filtered)

    def validate(self) -> bool:
        """Validate configuration settings."""
        if not self.project_name:
            raise ValueError("Project name cannot be empty")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
        valid_review_depths = ["basic", "standard", "comprehensive"]
        if self.review_depth not in valid_review_depths:
            raise ValueError(f"review_depth must be one of {valid_review_depths}")
        valid_generation_styles = ["minimal", "clean", "verbose"]
        if self.generation_style not in valid_generation_styles:
            raise ValueError(f"generation_style must be one of {valid_generation_styles}")
        return True
