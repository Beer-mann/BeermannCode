#!/usr/bin/env python3
"""
BeermannCode Autonomous Orchestrator

Scans projects, discovers tasks (TODOs, missing tests, missing docs),
routes them to the best Ollama model, executes fixes on feature branches,
and reports results.

Usage:
    python3 orchestrator.py                          # Full scan + execute
    python3 orchestrator.py --scan-only              # Scan only, no execution
    python3 orchestrator.py --project MegaRAG        # Single project
    python3 orchestrator.py --model qwen2.5-coder:7b # Force model
    python3 orchestrator.py --dry-run                # Show what would happen
    python3 orchestrator.py --list-models            # List available Ollama models
    python3 orchestrator.py --health                 # Health check + alert if down
    python3 orchestrator.py --security               # Security scan all projects
    python3 orchestrator.py --deps                   # Dependency scan
    python3 orchestrator.py --tests                  # Run all project tests
    python3 orchestrator.py --refactor               # Refactoring analysis
    python3 orchestrator.py --tier 2                 # Enable external models (1-4)
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from codeai_platform.config import CodeAIConfig, OLLAMA_MODELS, MODEL_ROUTING
from codeai_platform.modules.health_monitor import HealthMonitor
from codeai_platform.modules.security_scanner import SecurityScanner
from codeai_platform.modules.dependency_scanner import DependencyScanner
from codeai_platform.modules.test_runner import TestRunner
from codeai_platform.modules.refactorer import CodeRefactorer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/home/shares/beermann/logs/beermanncode-orchestrator.log", mode="a"),
    ],
)
log = logging.getLogger("orchestrator")

PROJECTS_DIR = Path("/home/shares/beermann/PROJECTS")
LOGS_DIR = Path("/home/shares/beermann/logs/beermanncode-tasks")
STATE_FILE = Path("/home/shares/beermann/logs/beermanncode-state.json")

# File patterns to scan
CODE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".cpp", ".c", ".h", ".cs", ".sh", ".bash"}
IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next", ".cache"}


@dataclass
class Task:
    id: str
    project: str
    task_type: str  # todo, fixme, missing_test, missing_docstring, missing_readme, lint
    file_path: str
    line: Optional[int] = None
    description: str = ""
    model: str = ""
    priority: int = 5  # 1=highest, 10=lowest
    status: str = "pending"  # pending, running, done, failed, skipped
    branch: str = ""
    result: str = ""
    created_at: str = ""
    completed_at: str = ""


@dataclass
class OrchestratorState:
    last_run: str = ""
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_skipped: int = 0
    total_scans: int = 0
    models_used: Dict[str, int] = field(default_factory=dict)

    def save(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls) -> "OrchestratorState":
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                return cls(**json.load(f))
        return cls()


class Orchestrator:
    def __init__(self, config: CodeAIConfig, dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.state = OrchestratorState.load()
        self.tasks: List[Task] = []
        self.health_monitor = HealthMonitor(config)
        self.security_scanner = SecurityScanner(config)
        self.dependency_scanner = DependencyScanner(config)
        self.test_runner = TestRunner(config)
        self.refactorer = CodeRefactorer(config)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # ── Model Management ──────────────────────────────────

    def check_ollama(self) -> bool:
        """Verify Ollama is reachable and list available models."""
        try:
            import urllib.request
            url = f"{self.config.ollama_host}/api/tags"
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read())
                available = [m["name"] for m in data.get("models", [])]
                log.info(f"Ollama online: {len(available)} models available")
                return True
        except Exception as e:
            log.error(f"Ollama unreachable at {self.config.ollama_host}: {e}")
            return False

    def list_models(self) -> List[Dict]:
        """List all available Ollama models with their capabilities."""
        try:
            import urllib.request
            url = f"{self.config.ollama_host}/api/tags"
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read())
                models = []
                for m in data.get("models", []):
                    name = m["name"]
                    info = OLLAMA_MODELS.get(name, {"type": "unknown", "speed": "unknown"})
                    models.append({
                        "name": name,
                        "size": m["details"].get("parameter_size", "?"),
                        "type": info.get("type", "unknown"),
                        "speed": info.get("speed", "unknown"),
                        "quant": m["details"].get("quantization_level", "?"),
                    })
                return models
        except Exception:
            return []

    def select_model(self, task: Task) -> str:
        ""
