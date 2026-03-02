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
        """Select the best model for a task based on type."""
        task_type_to_routing = {
            "todo": "code_generation",
            "fixme": "code_generation",
            "missing_test": "code_generation",
            "missing_docstring": "quick",
            "missing_readme": "general",
            "lint": "quick",
        }
        routing_key = task_type_to_routing.get(task.task_type, "general")
        return self.config.get_model_for_task(routing_key)

    # ── Project Scanning ──────────────────────────────────

    def scan_projects(self, project_filter: Optional[str] = None) -> List[Task]:
        """Scan all projects for actionable tasks."""
        tasks = []
        projects = list(PROJECTS_DIR.iterdir()) if PROJECTS_DIR.exists() else []

        for project_dir in sorted(projects):
            if not project_dir.is_dir() or project_dir.name.startswith("."):
                continue
            if project_filter and project_dir.name != project_filter:
                continue

            log.info(f"Scanning {project_dir.name}...")
            tasks.extend(self._scan_project(project_dir))

        self.tasks = tasks
        self.state.total_scans += 1
        log.info(f"Found {len(tasks)} tasks across {len(set(t.project for t in tasks))} projects")
        return tasks

    def _scan_project(self, project_dir: Path) -> List[Task]:
        """Scan a single project for tasks."""
        tasks = []
        now = datetime.now().isoformat()

        # Check for README
        if not (project_dir / "README.md").exists():
            tasks.append(Task(
                id=str(uuid.uuid4())[:8],
                project=project_dir.name,
                task_type="missing_readme",
                file_path=str(project_dir),
                description=f"Generate README.md for {project_dir.name}",
                priority=7,
                created_at=now,
            ))

        # Scan code files
        for file_path in project_dir.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix not in CODE_EXTENSIONS:
                continue
            if any(part in IGNORE_DIRS for part in file_path.parts):
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # TODOs and FIXMEs
            for i, line in enumerate(content.split("\n"), 1):
                if "TODO" in line and not line.strip().startswith("#!"):
                    tasks.append(Task(
                        id=str(uuid.uuid4())[:8],
                        project=project_dir.name,
                        task_type="todo",
                        file_path=str(file_path),
                        line=i,
                        description=line.strip(),
                        priority=5,
                        created_at=now,
                    ))
                elif "FIXME" in line:
                    tasks.append(Task(
                        id=str(uuid.uuid4())[:8],
                        project=project_dir.name,
                        task_type="fixme",
                        file_path=str(file_path),
                        line=i,
                        description=line.strip(),
                        priority=3,
                        created_at=now,
                    ))

            # Missing docstrings (Python)
            if file_path.suffix == ".py":
                functions_without_docs = self._find_undocumented_functions(content)
                if functions_without_docs:
                    tasks.append(Task(
                        id=str(uuid.uuid4())[:8],
                        project=project_dir.name,
                        task_type="missing_docstring",
                        file_path=str(file_path),
                        description=f"Add docstrings to: {', '.join(functions_without_docs[:5])}",
                        priority=8,
                        created_at=now,
                    ))

            # Missing tests (Python files without corresponding test)
            if file_path.suffix == ".py" and not file_path.name.startswith("test_") and file_path.name != "__init__.py":
                test_file = file_path.parent / f"test_{file_path.name}"
                tests_dir = project_dir / "tests" / f"test_{file_path.name}"
                if not test_file.exists() and not tests_dir.exists():
                    tasks.append(Task(
                        id=str(uuid.uuid4())[:8],
                        project=project_dir.name,
                        task_type="missing_test",
                        file_path=str(file_path),
                        description=f"Generate tests for {file_path.name}",
                        priority=6,
                        created_at=now,
                    ))

        return tasks

    def _find_undocumented_functions(self, code: str) -> List[str]:
        """Find Python functions/methods without docstrings."""
        undocumented = []
        lines = code.split("\n")
        for i, line in enumerate(lines):
            match = re.match(r"\s*def\s+(\w+)\s*\(", line)
            if match:
                func_name = match.group(1)
                if func_name.startswith("_") and func_name != "__init__":
                    continue
                # Check if next non-empty line is a docstring
                for j in range(i + 1, min(i + 3, len(lines))):
                    stripped = lines[j].strip()
                    if stripped:
                        if not (stripped.startswith('"""') or stripped.startswith("'''")):
                            undocumented.append(func_name)
                        break
        return undocumented

    # ── Task Execution ────────────────────────────────────

    def execute_tasks(self, max_tasks: int = 10, force_model: Optional[str] = None):
        """Execute pending tasks, sorted by priority."""
        if not self.tasks:
            log.info("No tasks to execute")
            return

        # Sort by priority (lower = higher priority)
        sorted_tasks = sorted(self.tasks, key=lambda t: t.priority)[:max_tasks]
        log.info(f"Executing {len(sorted_tasks)} tasks (max {max_tasks})")

        for task in sorted_tasks:
            model = force_model or self.select_model(task)
            task.model = model

            if self.dry_run:
                log.info(f"[DRY RUN] Would execute: [{task.task_type}] {task.description} → {model}")
                task.status = "skipped"
                continue

            try:
                self._execute_task(task)
            except Exception as e:
                log.error(f"Task {task.id} failed: {e}")
                task.status = "failed"
                task.result = str(e)
                self.state.tasks_failed += 1

        self.state.last_run = datetime.now().isoformat()
        self.state.save()
        self._save_report(sorted_tasks)

    def _execute_task(self, task: Task):
        """Execute a single task using Ollama."""
        log.info(f"Executing [{task.task_type}] in {task.project} with {task.model}")
        task.status = "running"

        # Create branch
        project_dir = PROJECTS_DIR / task.project
        branch_name = f"auto/{task.task_type}-{task.id}"
        task.branch = branch_name

        self._git_branch(project_dir, branch_name)

        try:
            if task.task_type in ("todo", "fixme"):
                result = self._fix_todo(task)
            elif task.task_type == "missing_test":
                result = self._generate_test(task)
            elif task.task_type == "missing_docstring":
                result = self._add_docstrings(task)
            elif task.task_type == "missing_readme":
                result = self._generate_readme(task)
            else:
                result = "Unknown task type"

            task.result = result
            task.status = "done"
            task.completed_at = datetime.now().isoformat()
            self.state.tasks_completed += 1
            self.state.models_used[task.model] = self.state.models_used.get(task.model, 0) + 1

            # Commit changes
            self._git_commit(project_dir, f"auto: {task.task_type} - {task.description[:60]}")
            log.info(f"✅ Task {task.id} completed on branch {branch_name}")

        except Exception as e:
            # Restore to main branch on failure
            self._git_checkout(project_dir, "main")
            raise

    def _fix_todo(self, task: Task) -> str:
        """Use Ollama to implement a TODO/FIXME."""
        file_path = Path(task.file_path)
        code = file_path.read_text(encoding="utf-8")

        prompt = (
            f"Fix this TODO/FIXME in the code. Return ONLY the complete updated file content, no explanations.\n\n"
            f"File: {file_path.name}\n"
            f"Line {task.line}: {task.description}\n\n"
            f"Full file:\n```\n{code[:6000]}\n```"
        )

        result = self._query_ollama(prompt, task.model)
        if result and len(result) > 50:
            # Extract code from response
            clean_code = self._extract_code(result, code)
            if clean_code:
                file_path.write_text(clean_code, encoding="utf-8")
                return f"Fixed TODO at line {task.line}"
        return "Could not generate fix"

    def _generate_test(self, task: Task) -> str:
        """Generate test file for a Python module."""
        file_path = Path(task.file_path)
        code = file_path.read_text(encoding="utf-8")

        prompt = (
            f"Generate comprehensive pytest tests for this Python module. "
            f"Return ONLY the test code, no explanations.\n\n"
            f"Module: {file_path.name}\n\n"
            f"```python\n{code[:6000]}\n```"
        )

        result = self._query_ollama(prompt, task.model)
        if result:
            test_code = self._extract_code(result)
            if test_code:
                test_path = file_path.parent / f"test_{file_path.name}"
                test_path.write_text(test_code, encoding="utf-8")
                return f"Generated tests: {test_path.name}"
        return "Could not generate tests"

    def _add_docstrings(self, task: Task) -> str:
        """Add docstrings to undocumented functions."""
        file_path = Path(task.file_path)
        code = file_path.read_text(encoding="utf-8")

        prompt = (
            f"Add Google-style docstrings to all public functions and methods in this file. "
            f"Return ONLY the complete updated file content, no explanations.\n\n"
            f"```python\n{code[:6000]}\n```"
        )

        result = self._query_ollama(prompt, task.model)
        if result:
            clean_code = self._extract_code(result, code)
            if clean_code:
                file_path.write_text(clean_code, encoding="utf-8")
                return "Added docstrings"
        return "Could not add docstrings"

    def _generate_readme(self, task: Task) -> str:
        """Generate README.md for a project."""
        project_dir = Path(task.file_path)

        # Gather project info
        files = []
        for f in project_dir.rglob("*"):
            if f.is_file() and not any(p in IGNORE_DIRS for p in f.parts):
                files.append(str(f.relative_to(project_dir)))

        prompt = (
            f"Generate a README.md for a project called '{task.project}'. "
            f"Based on these files: {', '.join(files[:30])}\n\n"
            f"Include: Project title, description, installation, usage, and structure. "
            f"Return ONLY the markdown content."
        )

        result = self._query_ollama(prompt, task.model)
        if result:
            readme_path = project_dir / "README.md"
            readme_path.write_text(result, encoding="utf-8")
            return "Generated README.md"
        return "Could not generate README"

    # ── Ollama Communication ──────────────────────────────

    def _query_ollama(self, prompt: str, model: str, timeout: int = 120) -> Optional[str]:
        """Send a prompt to Ollama and get a response."""
        import urllib.request

        url = f"{self.config.ollama_host}/api/generate"
        payload = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            }
        }).encode()

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
                return data.get("response", "")
        except Exception as e:
            log.error(f"Ollama query failed ({model}): {e}")
            return None

    def _extract_code(self, response: str, original: str = "") -> Optional[str]:
        """Extract code from an Ollama response, stripping markdown fences."""
        # Try to extract from code blocks
        match = re.search(r"```(?:\w+)?\n(.*?)```", response, re.DOTALL)
        if match:
            return match.group(1).strip() + "\n"
        # If response looks like raw code, use it directly
        if response.strip().startswith(("import ", "from ", "def ", "class ", "#!", "#!/")):
            return response.strip() + "\n"
        # If it's longer than original and has code-like content, use it
        if len(response) > len(original) * 0.5 and ("def " in response or "class " in response):
            return response.strip() + "\n"
        return None

    # ── Git Operations ────────────────────────────────────

    def _git_branch(self, project_dir: Path, branch_name: str):
        """Create and checkout a new branch."""
        try:
            # Ensure we're on main first
            subprocess.run(["git", "checkout", "main"], cwd=project_dir, capture_output=True)
            subprocess.run(["git", "checkout", "-b", branch_name], cwd=project_dir, capture_output=True, check=True)
            log.info(f"Created branch: {branch_name}")
        except subprocess.CalledProcessError:
            # Branch might exist, try checkout
            subprocess.run(["git", "checkout", branch_name], cwd=project_dir, capture_output=True)

    def _git_commit(self, project_dir: Path, message: str):
        """Stage all changes and commit."""
        subprocess.run(["git", "add", "-A"], cwd=project_dir, capture_output=True)
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=project_dir, capture_output=True, text=True
        )
        if result.returncode == 0:
            log.info(f"Committed: {message}")
        else:
            log.warning(f"Nothing to commit in {project_dir.name}")

    def _git_checkout(self, project_dir: Path, branch: str):
        """Checkout a branch."""
        subprocess.run(["git", "checkout", branch], cwd=project_dir, capture_output=True)

    # ── Reporting ─────────────────────────────────────────

    def _save_report(self, tasks: List[Task]):
        """Save execution report."""
        report_path = LOGS_DIR / f"report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        report = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": self.dry_run,
            "tasks": [asdict(t) for t in tasks],
            "summary": {
                "total": len(tasks),
                "done": sum(1 for t in tasks if t.status == "done"),
                "failed": sum(1 for t in tasks if t.status == "failed"),
                "skipped": sum(1 for t in tasks if t.status == "skipped"),
            }
        }
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        log.info(f"Report saved: {report_path}")

    def print_summary(self):
        """Print a summary of discovered tasks."""
        if not self.tasks:
            print("No tasks found.")
            return

        by_project = {}
        for t in self.tasks:
            by_project.setdefault(t.project, []).append(t)

        print(f"\n{'='*60}")
        print(f"  BeermannCode Orchestrator — {len(self.tasks)} Tasks Found")
        print(f"{'='*60}\n")

        for project, tasks in sorted(by_project.items()):
            print(f"📁 {project} ({len(tasks)} tasks)")
            by_type = {}
            for t in tasks:
                by_type.setdefault(t.task_type, []).append(t)
            for task_type, type_tasks in sorted(by_type.items()):
                model = self.select_model(type_tasks[0])
                print(f"   {task_type}: {len(type_tasks)} → {model}")
            print()

        print(f"Models that will be used:")
        model_counts = {}
        for t in self.tasks:
            m = self.select_model(t)
            model_counts[m] = model_counts.get(m, 0) + 1
        for model, count in sorted(model_counts.items(), key=lambda x: -x[1]):
            print(f"   {model}: {count} tasks")
        print()


    # ── New Module Commands ────────────────────────────────

    def run_health_check(self) -> str:
        """Run health check and return status."""
        health = self.health_monitor.check_health()
        summary = self.health_monitor.get_status_summary()
        log.info(summary.replace("\n", " | "))

        # Check if alert needed
        alert = self.health_monitor.should_alert()
        if alert:
            log.warning(f"ALERT: {alert[:100]}")
        return summary

    def run_security_scan(self, project_filter: Optional[str] = None):
        """Run security scan across projects."""
        projects = list(PROJECTS_DIR.iterdir()) if PROJECTS_DIR.exists() else []
        total_findings = 0

        print(f"\n{'='*60}")
        print(f"  🔒 Security Scan")
        print(f"{'='*60}\n")

        for project_dir in sorted(projects):
            if not project_dir.is_dir() or project_dir.name.startswith("."):
                continue
            if project_filter and project_dir.name != project_filter:
                continue

            result = self.security_scanner.scan_project(str(project_dir))
            total_findings += len(result.findings)

            icon = "🔴" if result.critical_count > 0 else "🟡" if result.high_count > 0 else "🟢"
            print(f"{icon} {result.project}: {len(result.findings)} findings "
                  f"({result.critical_count} critical, {result.high_count} high) "
                  f"Risk: {result.risk_score:.0f}/100")

            for f in result.findings[:3]:
                print(f"   {f.severity.upper()}: {f.title} ({f.file_path}:{f.line})")

        print(f"\nTotal: {total_findings} findings across {len(projects)} projects")

    def run_dependency_scan(self, project_filter: Optional[str] = None):
        """Run dependency scan across projects."""
        projects = list(PROJECTS_DIR.iterdir()) if PROJECTS_DIR.exists() else []

        print(f"\n{'='*60}")
        print(f"  📦 Dependency Scan")
        print(f"{'='*60}\n")

        for project_dir in sorted(projects):
            if not project_dir.is_dir() or project_dir.name.startswith("."):
                continue
            if project_filter and project_dir.name != project_filter:
                continue

            result = self.dependency_scanner.scan_project(str(project_dir))
            if result.total_deps == 0:
                continue

            print(f"📁 {result.project}: {result.total_deps} deps ({', '.join(result.ecosystems)})")
            if result.outdated_count:
                print(f"   ⚠️ {result.outdated_count} outdated")
            if result.unused_imports:
                print(f"   🗑️ {len(result.unused_imports)} unused imports")
                for imp in result.unused_imports[:3]:
                    print(f"      {imp['file']}:{imp['line']} → {imp['import']}")
            print()

    def run_tests(self, project_filter: Optional[str] = None):
        """Run tests across projects."""
        print(f"\n{'='*60}")
        print(f"  🧪 Test Runner")
        print(f"{'='*60}\n")

        projects = PROJECTS_DIR if PROJECTS_DIR.exists() else Path(".")

        for project_dir in sorted(projects.iterdir()):
            if not project_dir.is_dir() or project_dir.name.startswith("."):
                continue
            if project_filter and project_dir.name != project_filter:
                continue

            fw = self.test_runner.detect_framework(str(project_dir))
            if not fw:
                continue

            print(f"🧪 {project_dir.name} ({fw})... ", end="", flush=True)
            result = self.test_runner.run_tests(str(project_dir))

            if result.total > 0:
                icon = "✅" if result.failed == 0 else "❌"
                print(f"{icon} {result.passed}/{result.total} passed ({result.duration_seconds:.1f}s)")
                for f in result.failures[:2]:
                    print(f"   FAIL: {f['test']}")
            else:
                print("⏭️ No tests found")

    def run_refactor_analysis(self, project_filter: Optional[str] = None):
        """Run refactoring analysis across projects."""
        print(f"\n{'='*60}")
        print(f"  🔧 Refactoring Analysis")
        print(f"{'='*60}\n")

        for project_dir in sorted(PROJECTS_DIR.iterdir()):
            if not project_dir.is_dir() or project_dir.name.startswith("."):
                continue
            if project_filter and project_dir.name != project_filter:
                continue

            results = self.refactorer.analyze_project(str(project_dir))
            total_suggestions = sum(len(r.suggestions) for r in results)
            total_smells = sum(len(r.code_smells) for r in results)
            total_dupes = sum(len(r.duplications) for r in results)
            total_hotspots = sum(len(r.complexity_hotspots) for r in results)

            if total_suggestions + total_smells + total_dupes + total_hotspots == 0:
                continue

            print(f"📁 {project_dir.name}:")
            if total_suggestions:
                print(f"   💡 {total_suggestions} refactoring suggestions")
            if total_smells:
                print(f"   👃 {total_smells} code smells")
            if total_dupes:
                print(f"   📋 {total_dupes} duplications")
            if total_hotspots:
                print(f"   🔥 {total_hotspots} complexity hotspots")

            # Show top suggestions
            all_suggestions = [s for r in results for s in r.suggestions]
            for s in sorted(all_suggestions, key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.severity, 3))[:3]:
                print(f"      [{s.severity}] {s.description[:80]}")
            print()


def main():
    parser = argparse.ArgumentParser(description="BeermannCode Autonomous Orchestrator")
    parser.add_argument("--project", help="Scan only this project")
    parser.add_argument("--model", help="Force a specific model for all tasks")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")
    parser.add_argument("--scan-only", action="store_true", help="Scan only, don't execute")
    parser.add_argument("--list-models", action="store_true", help="List available Ollama models")
    parser.add_argument("--max-tasks", type=int, default=10, help="Max tasks to execute")
    parser.add_argument("--health", action="store_true", help="Health check")
    parser.add_argument("--security", action="store_true", help="Security scan")
    parser.add_argument("--deps", action="store_true", help="Dependency scan")
    parser.add_argument("--tests", action="store_true", help="Run project tests")
    parser.add_argument("--refactor", action="store_true", help="Refactoring analysis")
    parser.add_argument("--tier", type=int, default=1, help="Max model tier (1=Ollama, 2-4=external)")
    parser.add_argument("--all", action="store_true", help="Run all analyses")
    args = parser.parse_args()

    config = CodeAIConfig.from_file(str(Path(__file__).parent / "config.json"))
    if args.tier > 1:
        config.enable_external = True
        config.max_tier = args.tier
        log.info(f"External models enabled up to tier {args.tier}")

    orchestrator = Orchestrator(config, dry_run=args.dry_run)

    # Health check (always first)
    if args.health or args.all:
        print(orchestrator.run_health_check())
        if not args.all:
            return

    # Security scan
    if args.security or args.all:
        orchestrator.run_security_scan(args.project)
        if not args.all:
            return

    # Dependency scan
    if args.deps or args.all:
        orchestrator.run_dependency_scan(args.project)
        if not args.all:
            return

    # Test runner
    if args.tests or args.all:
        orchestrator.run_tests(args.project)
        if not args.all:
            return

    # Refactoring analysis
    if args.refactor or args.all:
        orchestrator.run_refactor_analysis(args.project)
        if not args.all:
            return

    if args.list_models:
        models = orchestrator.list_models()
        print(f"\n{'='*60}")
        print(f"  Ollama Models on {config.ollama_host}")
        print(f"{'='*60}\n")
        for m in models:
            print(f"  {m['name']:35s} {m['size']:>6s}  {m['type']:10s}  {m['speed']:8s}  Q:{m['quant']}")
        print()
        return

    if not orchestrator.check_ollama():
        log.error("Cannot proceed without Ollama. Exiting.")
        sys.exit(1)

    tasks = orchestrator.scan_projects(args.project)
    orchestrator.print_summary()

    if args.scan_only:
        return

    orchestrator.execute_tasks(max_tasks=args.max_tasks, force_model=args.model)


if __name__ == "__main__":
    main()
