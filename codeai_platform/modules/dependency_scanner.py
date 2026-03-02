"""
Dependency scanner module for CodeAI Platform.
Scans projects for outdated, vulnerable, or unused dependencies.
"""

import json
import subprocess
import re
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Dependency:
    """A project dependency."""
    name: str
    current_version: str = ""
    latest_version: str = ""
    is_outdated: bool = False
    is_dev: bool = False
    source_file: str = ""
    ecosystem: str = ""  # pip, npm, cargo, go

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "current": self.current_version,
            "latest": self.latest_version,
            "outdated": self.is_outdated,
            "dev": self.is_dev,
            "ecosystem": self.ecosystem,
        }


@dataclass
class DependencyScanResult:
    """Result of dependency scanning."""
    project: str
    ecosystems: List[str] = field(default_factory=list)
    dependencies: List[Dependency] = field(default_factory=list)
    outdated_count: int = 0
    unused_imports: List[Dict] = field(default_factory=list)
    license_issues: List[Dict] = field(default_factory=list)
    total_deps: int = 0

    def to_dict(self) -> Dict:
        return {
            "project": self.project,
            "ecosystems": self.ecosystems,
            "total_deps": self.total_deps,
            "outdated_count": self.outdated_count,
            "dependencies": [d.to_dict() for d in self.dependencies],
            "unused_imports": self.unused_imports,
        }


class DependencyScanner:
    """Scans project dependencies for issues."""

    def __init__(self, config):
        self.config = config

    def scan_project(self, project_path: str) -> DependencyScanResult:
        """Scan a project for dependency info."""
        project = Path(project_path)
        result = DependencyScanResult(project=project.name)

        # Python
        req_files = list(project.glob("requirements*.txt"))
        if req_files or (project / "pyproject.toml").exists() or (project / "setup.py").exists():
            result.ecosystems.append("pip")
            deps = self._scan_python(project)
            result.dependencies.extend(deps)

        # JavaScript/TypeScript
        if (project / "package.json").exists():
            result.ecosystems.append("npm")
            deps = self._scan_npm(project)
            result.dependencies.extend(deps)

        # Go
        if (project / "go.mod").exists():
            result.ecosystems.append("go")
            deps = self._scan_go(project)
            result.dependencies.extend(deps)

        # Rust
        if (project / "Cargo.toml").exists():
            result.ecosystems.append("cargo")
            deps = self._scan_cargo(project)
            result.dependencies.extend(deps)

        result.total_deps = len(result.dependencies)
        result.outdated_count = sum(1 for d in result.dependencies if d.is_outdated)

        # Scan for unused imports (Python)
        if "pip" in result.ecosystems:
            result.unused_imports = self._find_unused_imports(project)

        return result

    def scan_all_projects(self, projects_dir: str) -> List[DependencyScanResult]:
        """Scan all projects in a directory."""
        results = []
        for project_dir in sorted(Path(projects_dir).iterdir()):
            if project_dir.is_dir() and not project_dir.name.startswith("."):
                results.append(self.scan_project(str(project_dir)))
        return results

    def _scan_python(self, project: Path) -> List[Dependency]:
        """Parse Python requirements files."""
        deps = []

        for req_file in project.glob("requirements*.txt"):
            is_dev = "dev" in req_file.name
            content = req_file.read_text(errors="ignore")
            for line in content.split("\n"):
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                # Parse: package==1.0.0, package>=1.0, package
                match = re.match(r"^([a-zA-Z0-9_.-]+)\s*([><=!~]+)?\s*([\d.a-zA-Z*]+)?", line)
                if match:
                    deps.append(Dependency(
                        name=match.group(1),
                        current_version=match.group(3) or "unspecified",
                        is_dev=is_dev,
                        source_file=str(req_file),
                        ecosystem="pip",
                    ))

        # pyproject.toml
        pyproject = project / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text(errors="ignore")
            # Simple parse for dependencies = ["pkg>=1.0"]
            dep_section = re.findall(r'"([a-zA-Z0-9_.-]+)(?:[><=!~]+[\d.]+)?"', content)
            for name in dep_section:
                if name not in [d.name for d in deps]:
                    deps.append(Dependency(name=name, ecosystem="pip", source_file=str(pyproject)))

        return deps

    def _scan_npm(self, project: Path) -> List[Dependency]:
        """Parse package.json dependencies."""
        deps = []
        pkg_file = project / "package.json"

        try:
            pkg = json.loads(pkg_file.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return deps

        for section, is_dev in [("dependencies", False), ("devDependencies", True)]:
            for name, version in pkg.get(section, {}).items():
                deps.append(Dependency(
                    name=name,
                    current_version=version.lstrip("^~>="),
                    is_dev=is_dev,
                    source_file=str(pkg_file),
                    ecosystem="npm",
                ))

        return deps

    def _scan_go(self, project: Path) -> List[Dependency]:
        """Parse go.mod."""
        deps = []
        go_mod = project / "go.mod"

        content = go_mod.read_text(errors="ignore")
        for match in re.finditer(r"^\s+(\S+)\s+(v[\d.]+)", content, re.MULTILINE):
            deps.append(Dependency(
                name=match.group(1),
                current_version=match.group(2),
                source_file=str(go_mod),
                ecosystem="go",
            ))

        return deps

    def _scan_cargo(self, project: Path) -> List[Dependency]:
        """Parse Cargo.toml."""
        deps = []
        cargo = project / "Cargo.toml"

        content = cargo.read_text(errors="ignore")
        in_deps = False
        for line in content.split("\n"):
            if re.match(r"\[.*dependencies.*\]", line):
                in_deps = True
                continue
            if line.startswith("["):
                in_deps = False
                continue
            if in_deps:
                match = re.match(r'(\w+)\s*=\s*"([\d.]+)"', line)
                if match:
                    deps.append(Dependency(
                        name=match.group(1),
                        current_version=match.group(2),
                        source_file=str(cargo),
                        ecosystem="cargo",
                    ))

        return deps

    def _find_unused_imports(self, project: Path) -> List[Dict]:
        """Find potentially unused imports in Python files."""
        unused = []
        ignore = {".git", "node_modules", "__pycache__", ".venv", "venv"}

        for py_file in project.rglob("*.py"):
            if any(p in ignore for p in py_file.parts):
                continue
            try:
                content = py_file.read_text(errors="ignore")
            except Exception:
                continue

            lines = content.split("\n")
            imports = []

            for i, line in enumerate(lines):
                # import foo / from foo import bar
                match = re.match(r"^(?:from\s+\S+\s+)?import\s+(.+)", line.strip())
                if match:
                    imported = match.group(1).split(",")
                    for imp in imported:
                        name = imp.strip().split(" as ")[-1].strip()
                        if name and name != "*":
                            imports.append((name, i + 1))

            # Check if imported names are used in the rest of the code
            for name, line_num in imports:
                # Count occurrences (excluding the import line itself)
                rest = "\n".join(lines[:line_num-1] + lines[line_num:])
                # Simple word boundary check
                if not re.search(rf"\b{re.escape(name)}\b", rest):
                    unused.append({
                        "file": str(py_file.relative_to(project)),
                        "import": name,
                        "line": line_num,
                    })

        return unused[:50]  # Cap results
