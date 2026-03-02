"""
Test runner module for CodeAI Platform.
Discovers, runs, and reports on project tests. Auto-generates missing tests.
"""

import subprocess
import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestResult:
    """Result of a test run."""
    project: str
    framework: str  # pytest, jest, go-test, cargo-test
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    duration_seconds: float = 0.0
    failures: List[Dict] = None
    coverage_percent: float = 0.0
    raw_output: str = ""

    def __post_init__(self):
        if self.failures is None:
            self.failures = []

    @property
    def success_rate(self) -> float:
        return (self.passed / self.total * 100) if self.total else 0.0

    def to_dict(self) -> Dict:
        return {
            "project": self.project,
            "framework": self.framework,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "skipped": self.skipped,
            "success_rate": f"{self.success_rate:.1f}%",
            "duration": f"{self.duration_seconds:.2f}s",
            "coverage": f"{self.coverage_percent:.1f}%",
            "failures": self.failures,
        }


class TestRunner:
    """Discovers and runs tests across projects."""

    def __init__(self, config):
        self.config = config

    def detect_framework(self, project_path: str) -> Optional[str]:
        """Detect which test framework a project uses."""
        project = Path(project_path)

        # Python
        if (project / "pytest.ini").exists() or (project / "setup.cfg").exists():
            return "pytest"
        if (project / "pyproject.toml").exists():
            content = (project / "pyproject.toml").read_text(errors="ignore")
            if "pytest" in content:
                return "pytest"
        if any(project.rglob("test_*.py")):
            return "pytest"

        # JavaScript/TypeScript
        pkg_json = project / "package.json"
        if pkg_json.exists():
            try:
                pkg = json.loads(pkg_json.read_text())
                scripts = pkg.get("scripts", {})
                if "test" in scripts:
                    test_cmd = scripts["test"]
                    if "jest" in test_cmd:
                        return "jest"
                    if "mocha" in test_cmd:
                        return "mocha"
                    if "vitest" in test_cmd:
                        return "vitest"
                deps = {**pkg.get("devDependencies", {}), **pkg.get("dependencies", {})}
                if "jest" in deps:
                    return "jest"
            except json.JSONDecodeError:
                pass

        # Go
        if any(project.rglob("*_test.go")):
            return "go-test"

        # Rust
        if (project / "Cargo.toml").exists():
            return "cargo-test"

        return None

    def run_tests(self, project_path: str, framework: Optional[str] = None) -> TestResult:
        """Run tests for a project."""
        project = Path(project_path)
        fw = framework or self.detect_framework(project_path)

        if not fw:
            return TestResult(project=project.name, framework="none", raw_output="No test framework detected")

        runners = {
            "pytest": self._run_pytest,
            "jest": self._run_jest,
            "go-test": self._run_go_test,
            "cargo-test": self._run_cargo_test,
        }

        runner = runners.get(fw)
        if not runner:
            return TestResult(project=project.name, framework=fw, raw_output=f"Runner not implemented: {fw}")

        return runner(project_path)

    def run_all_projects(self, projects_dir: str) -> List[TestResult]:
        """Run tests across all projects."""
        results = []
        projects = Path(projects_dir)

        for project_dir in sorted(projects.iterdir()):
            if not project_dir.is_dir() or project_dir.name.startswith("."):
                continue

            fw = self.detect_framework(str(project_dir))
            if fw:
                result = self.run_tests(str(project_dir), fw)
                results.append(result)

        return results

    def _run_pytest(self, project_path: str) -> TestResult:
        """Run pytest and parse results."""
        project = Path(project_path)
        result = TestResult(project=project.name, framework="pytest")

        try:
            proc = subprocess.run(
                ["python3", "-m", "pytest", "--tb=short", "-q", "--no-header"],
                cwd=project_path,
                capture_output=True, text=True, timeout=120,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            result.raw_output = proc.stdout + proc.stderr

            # Parse pytest output
            import re
            # "5 passed, 2 failed, 1 error in 1.23s"
            summary = re.search(
                r"(\d+)\s+passed(?:.*?(\d+)\s+failed)?(?:.*?(\d+)\s+error)?(?:.*?(\d+)\s+skipped)?.*?in\s+([\d.]+)s",
                result.raw_output
            )
            if summary:
                result.passed = int(summary.group(1))
                result.failed = int(summary.group(2) or 0)
                result.errors = int(summary.group(3) or 0)
                result.skipped = int(summary.group(4) or 0)
                result.duration_seconds = float(summary.group(5))
                result.total = result.passed + result.failed + result.errors + result.skipped

            # Extract failure details
            if result.failed > 0:
                failures = re.findall(r"FAILED\s+(.*?)\s+-\s+(.*?)$", result.raw_output, re.MULTILINE)
                result.failures = [{"test": f[0], "reason": f[1]} for f in failures]

        except subprocess.TimeoutExpired:
            result.raw_output = "Tests timed out after 120s"
            result.errors = 1
        except FileNotFoundError:
            result.raw_output = "pytest not found"

        return result

    def _run_jest(self, project_path: str) -> TestResult:
        """Run Jest and parse results."""
        project = Path(project_path)
        result = TestResult(project=project.name, framework="jest")

        try:
            proc = subprocess.run(
                ["npx", "jest", "--json", "--no-coverage"],
                cwd=project_path,
                capture_output=True, text=True, timeout=120,
            )

            try:
                data = json.loads(proc.stdout)
                result.total = data.get("numTotalTests", 0)
                result.passed = data.get("numPassedTests", 0)
                result.failed = data.get("numFailedTests", 0)
                result.skipped = data.get("numPendingTests", 0)

                for suite in data.get("testResults", []):
                    for test in suite.get("assertionResults", []):
                        if test.get("status") == "failed":
                            result.failures.append({
                                "test": test.get("fullName", ""),
                                "reason": "\n".join(test.get("failureMessages", [])),
                            })
            except json.JSONDecodeError:
                result.raw_output = proc.stdout + proc.stderr

        except subprocess.TimeoutExpired:
            result.raw_output = "Tests timed out"
            result.errors = 1
        except FileNotFoundError:
            result.raw_output = "npx/jest not found"

        return result

    def _run_go_test(self, project_path: str) -> TestResult:
        """Run go test."""
        project = Path(project_path)
        result = TestResult(project=project.name, framework="go-test")

        try:
            proc = subprocess.run(
                ["go", "test", "-v", "-count=1", "./..."],
                cwd=project_path,
                capture_output=True, text=True, timeout=120,
            )
            result.raw_output = proc.stdout + proc.stderr

            import re
            passed = len(re.findall(r"--- PASS:", result.raw_output))
            failed = len(re.findall(r"--- FAIL:", result.raw_output))
            result.passed = passed
            result.failed = failed
            result.total = passed + failed

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            result.raw_output = str(e)

        return result

    def _run_cargo_test(self, project_path: str) -> TestResult:
        """Run cargo test."""
        project = Path(project_path)
        result = TestResult(project=project.name, framework="cargo-test")

        try:
            proc = subprocess.run(
                ["cargo", "test"],
                cwd=project_path,
                capture_output=True, text=True, timeout=180,
            )
            result.raw_output = proc.stdout + proc.stderr

            import re
            summary = re.search(r"test result:.*?(\d+) passed.*?(\d+) failed", result.raw_output)
            if summary:
                result.passed = int(summary.group(1))
                result.failed = int(summary.group(2))
                result.total = result.passed + result.failed

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            result.raw_output = str(e)

        return result
