"""
CodeAI Platform - AI-powered assistant for software development projects.

This platform provides intelligent code analysis, generation, and review capabilities
specifically designed for software projects.
"""

__version__ = "1.0.0"
__author__ = "BeermannCode"

from .config import CodeAIConfig
from .analyzer import CodeAnalyzer
from .generator import CodeGenerator
from .reviewer import CodeReviewer

__all__ = [
    "CodeAIConfig",
    "CodeAnalyzer", 
    "CodeGenerator",
    "CodeReviewer"
]
