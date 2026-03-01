"""
CodeAI Platform - AI-powered assistant for software development projects.

This platform provides intelligent code analysis, generation, and review capabilities
specifically designed for software projects.
"""

__version__ = "1.0.0"
__author__ = "BeermannCode"

from .config import CodeAIConfig
from .modules.analyzer import CodeAnalyzer
from .modules.generator import CodeGenerator
from .modules.reviewer import CodeReviewer

__all__ = [
    "CodeAIConfig",
    "CodeAnalyzer", 
    "CodeGenerator",
    "CodeReviewer"
]
