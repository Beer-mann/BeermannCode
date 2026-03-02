"""
CodeAI Platform - AI-powered assistant for software development projects.

Modules:
- Analyzer: Code quality, complexity, and issue detection
- Generator: AI-powered code generation
- Reviewer: Automated code review
- Refactorer: Code smell detection and refactoring suggestions
- TestRunner: Multi-framework test discovery and execution
- DependencyScanner: Dependency analysis and unused import detection
- SecurityScanner: Vulnerability scanning (secrets, injection, crypto)
- HealthMonitor: Ollama and system health monitoring
"""

__version__ = "2.0.0"
__author__ = "BeermannCode"

from .config import CodeAIConfig
from .modules.analyzer import CodeAnalyzer
from .modules.generator import CodeGenerator
from .modules.reviewer import CodeReviewer
from .modules.refactorer import CodeRefactorer
from .modules.test_runner import TestRunner
from .modules.dependency_scanner import DependencyScanner
from .modules.security_scanner import SecurityScanner
from .modules.health_monitor import HealthMonitor

__all__ = [
    "CodeAIConfig",
    "CodeAnalyzer",
    "CodeGenerator",
    "CodeReviewer",
    "CodeRefactorer",
    "TestRunner",
    "DependencyScanner",
    "SecurityScanner",
    "HealthMonitor",
]
