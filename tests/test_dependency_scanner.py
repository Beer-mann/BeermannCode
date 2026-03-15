"""Tests for codeai_platform.modules.dependency_scanner module."""

import json

from codeai_platform.config import CodeAIConfig
from codeai_platform.modules.dependency_scanner import (
    Dependency,
    DependencyScanResult,
    DependencyScanner,
)


def make_config():
    config = CodeAIConfig()
    config.get_openai_client = lambda use_real=False: None
    return config


def make_scanner():
    return DependencyScanner(make_config())


class TestDependencyModels:
    def test_dependency_to_dict(self):
        dep = Dependency(
            name="pytest",
            current_version="8.0.0",
            latest_version="8.2.0",
            is_outdated=True,
            is_dev=True,
            ecosystem="pip",
        )

        assert dep.to_dict() == {
            "name": "pytest",
            "current": "8.0.0",
            "latest": "8.2.0",
            "outdated": True,
            "dev": True,
            "ecosystem": "pip",
        }

    def test_scan_result_to_dict_includes_dependencies(self):
        result = DependencyScanResult(
            project="demo",
            ecosystems=["pip"],
            dependencies=[Dependency(name="flask", ecosystem="pip")],
            total_deps=1,
        )

        payload = result.to_dict()

        assert payload["project"] == "demo"
        assert payload["ecosystems"] == ["pip"]
        assert payload["total_deps"] == 1
        assert payload["dependencies"][0]["name"] == "flask"


class TestDependencyScanner:
    def test_scan_project_detects_multiple_ecosystems_and_unused_imports(self, tmp_path):
        project = tmp_path / "sample_project"
        project.mkdir()
        (project / "requirements.txt").write_text("flask==3.0.0\nrequests>=2.31.0\n")
        (project / "requirements-dev.txt").write_text("pytest==8.0.0\n")
        (project / "package.json").write_text(
            json.dumps(
                {
                    "dependencies": {"react": "^18.2.0"},
                    "devDependencies": {"jest": "~29.0.0"},
                }
            )
        )
        (project / "go.mod").write_text(
            "module example.com/demo\n\nrequire (\n\tgithub.com/pkg/errors v0.9.1\n)\n"
        )
        (project / "Cargo.toml").write_text(
            "[package]\nname = \"demo\"\nversion = \"0.1.0\"\n\n[dependencies]\nserde = \"1.0\"\n"
        )
        (project / "main.py").write_text("import os\nimport json\n\nprint(os.getcwd())\n")

        result = make_scanner().scan_project(str(project))

        assert set(result.ecosystems) == {"pip", "npm", "go", "cargo"}
        assert result.total_deps == 7
        assert result.outdated_count == 0
        assert any(dep.name == "pytest" and dep.is_dev for dep in result.dependencies)
        assert any(dep.name == "react" and dep.ecosystem == "npm" for dep in result.dependencies)
        assert any(item["import"] == "json" for item in result.unused_imports)

    def test_scan_python_deduplicates_pyproject_dependencies(self, tmp_path):
        project = tmp_path / "python_project"
        project.mkdir()
        (project / "requirements.txt").write_text("flask==3.0.0\n")
        (project / "pyproject.toml").write_text(
            "[project]\ndependencies = [\"flask>=3.0\", \"httpx>=0.27\"]\n"
        )

        deps = make_scanner()._scan_python(project)

        assert [dep.name for dep in deps].count("flask") == 1
        assert any(dep.name == "httpx" for dep in deps)

    def test_scan_npm_returns_empty_for_invalid_json(self, tmp_path):
        project = tmp_path / "node_project"
        project.mkdir()
        (project / "package.json").write_text("{invalid json")

        assert make_scanner()._scan_npm(project) == []

    def test_find_unused_imports_ignores_virtualenv_directories(self, tmp_path):
        project = tmp_path / "project"
        project.mkdir()
        (project / "app.py").write_text("import os\n")
        venv_dir = project / ".venv"
        venv_dir.mkdir()
        (venv_dir / "ignored.py").write_text("import definitely_unused\n")

        unused = make_scanner()._find_unused_imports(project)

        assert len(unused) == 1
        assert unused[0]["file"] == "app.py"
        assert unused[0]["import"] == "os"

    def test_scan_all_projects_skips_hidden_directories(self, tmp_path, monkeypatch):
        visible = tmp_path / "visible"
        hidden = tmp_path / ".hidden"
        visible.mkdir()
        hidden.mkdir()
        scanner = make_scanner()
        seen = []

        def fake_scan_project(path):
            seen.append(path)
            return DependencyScanResult(project="ok")

        monkeypatch.setattr(scanner, "scan_project", fake_scan_project)

        results = scanner.scan_all_projects(str(tmp_path))

        assert len(results) == 1
        assert seen == [str(visible)]
