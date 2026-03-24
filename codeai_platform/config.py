"""
Configuration module for CodeAI Platform.
Manages AI model settings and project-specific configurations.
"""

from typing import Dict, Optional, List
from dataclasses import dataclass, field


@dataclass
class CodeAIConfig:
    """Configuration for CodeAI Platform."""
    
    project_name: str = "default_project"
    project_type: str = "general"  # general, web, mobile, data_science, etc.
    supported_languages: List[str] = field(default_factory=lambda: ["python", "javascript", "java"])
    
    # AI Model Settings
    model_name: str = "codeai-v1"
    openai_model: str = "gpt-4o-mini"
    max_tokens: int = 2048
    temperature: float = 0.7
    
    # Analysis Settings
    enable_code_analysis: bool = True
    enable_code_generation: bool = True
    enable_code_review: bool = True
    
    # Review Settings
    review_depth: str = "standard"  # basic, standard, comprehensive
    auto_fix_issues: bool = False
    
    # Generation Settings
    generation_style: str = "clean"  # minimal, clean, verbose
    include_comments: bool = True
    include_tests: bool = True
    
    def to_dict(self) -> Dict:
        """Convert configuration to dictionary."""
        return {
            "project_name": self.project_name,
            "project_type": self.project_type,
            "supported_languages": self.supported_languages,
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "enable_code_analysis": self.enable_code_analysis,
            "enable_code_generation": self.enable_code_generation,
            "enable_code_review": self.enable_code_review,
            "review_depth": self.review_depth,
            "auto_fix_issues": self.auto_fix_issues,
            "generation_style": self.generation_style,
            "include_comments": self.include_comments,
            "include_tests": self.include_tests
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> "CodeAIConfig":
        """Create configuration from dictionary."""
        return cls(**config_dict)
    
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

    def get_openai_client(self):
        """Return an OpenAI client if OPENAI_API_KEY is set, otherwise None."""
        import os
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        try:
            from openai import OpenAI
            return OpenAI(api_key=api_key)
        except ImportError:
            return None
