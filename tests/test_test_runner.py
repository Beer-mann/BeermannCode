"""Tests for codeai_platform.modules.test_runner module."""

import json
import subprocess
from types import SimpleNamespace

from codeai_platform.config import CodeAIConfig
from codeai_platform.modules.test_runner import TestResult, TestRunner


def make_config():
    config = CodeAIConfig()
    config.get_openai_client = lambda use_real=False: None
    return config


def make_runner():
    return TestRunner(make_config())


class TestTestResult:
    def test_success_rate_and_to_dict(self):
        result = TestResult(project="demo", framework="pytest", total=5, passed=4, failed=1)

        assert result.success_rate == 80.0
        payload = result.to_dict()
        assert payload["success_rate"] == "80.0%"
        assert payload["coverage"] == "0.0%"


class TestDetectFramework:
    def test_detects_pytest_from_test_files(self, tmp_path):
        (tmp_path / "test_sample.py").write_text("def test_ok():\n    assert True\n")

        assert make_runner().detect_framework(str(tmp_path)) == "pytest"

    def test_detects_jest_from_package_json(self, tmp_path):
        (tmp_path / "package.json").write_text(
            json.dumps({"scripts": {"test": "jest --runInBand"}})
        )

        assert make_runner().detect_framework(str(tmp_path)) == "jest"

    def test_detects_go_and_cargo_projects(self, tmp_path):
        go_project = tmp_path / "go_project"
        cargo_project = tmp_path / "cargo_project"
        go_project.mkdir()
        cargo_project.mkdir()
        (go_project / "main_test.go").write_text("package main\n")
        (cargo_project / "Cargo.toml").write_text("[package]\nname='demo'\nversion='0.1.0'\n")

        assert make_runner().detect_framework(str(go_project)) == "go-test"
        assert make_runner().detect_framework(str(cargo_project)) == "cargo-test"

    def test_returns_none_when_no_framework_detected(self, tmp_path):
        assert make_runner().detect_framework(str(tmp_path)) is None


class TestRunTests:
    def test_run_tests_returns_none_result_when_framework_missing(self, tmp_path):
        result = make_runner().run_tests(str(tmp_path))

        assert result.framework == "none"
        assert result.raw_output == "No test framework detected"

    def test_run_tests_handles_unimplemented_framework(self, tmp_path):
        result = make_runner().run_tests(str(tmp_path), framework="mocha")

        assert result.framework == "mocha"
        assert "Runner not implemented" in result.raw_output

    def test_run_all_projects_runs_only_detected_frameworks(self, tmp_path, monkeypatch):
        project_a = tmp_path / "a"
        project_b = tmp_path / "b"
        project_a.mkdir()
        project_b.mkdir()
        runner = make_runner()

        monkeypatch.setattr(
            runner,
            "detect_framework",
            lambda path: "pytest" if path.endswith("/a") else None,
        )
        monkeypatch.setattr(
            runner,
            "run_tests",
            lambda path, framework=None: TestResult(project="a", framework=framework or "pytest"),
        )

        results = runner.run_all_projects(str(tmp_path))

        assert len(results) == 1
        assert results[0].framework == "pytest"


class TestFrameworkRunners:
    def test_run_pytest_parses_summary_and_failures(self, monkeypatch, tmp_path):
        output = (
            "..F\n"
            "FAILED tests/test_example.py::test_fail - AssertionError: boom\n"
            "2 passed, 1 failed, 1 skipped in 1.23s\n"
        )
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *args, **kwargs: SimpleNamespace(stdout=output, stderr=""),
        )

        result = make_runner()._run_pytest(str(tmp_path))

        assert result.passed == 2
        assert result.failed == 1
        assert result.skipped == 1
        assert result.total == 4
        assert result.duration_seconds == 1.23
        assert result.failures == [
            {"test": "tests/test_example.py::test_fail", "reason": "AssertionError: boom"}
        ]

    def test_run_pytest_handles_timeout(self, monkeypatch, tmp_path):
        def raise_timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="pytest", timeout=120)

        monkeypatch.setattr(subprocess, "run", raise_timeout)

        result = make_runner()._run_pytest(str(tmp_path))

        assert result.errors == 1
        assert "timed out" in result.raw_output.lower()

    def test_run_jest_parses_json_results(self, monkeypatch, tmp_path):
        payload = {
            "numTotalTests": 3,
            "numPassedTests": 2,
            "numFailedTests": 1,
            "numPendingTests": 0,
            "testResults": [
                {
                    "assertionResults": [
                        {"status": "passed", "fullName": "suite ok", "failureMessages": []},
                        {
                            "status": "failed",
                            "fullName": "suite fail",
                            "failureMessages": ["expected true to be false"],
                        },
                    ]
                }
            ],
        }
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *args, **kwargs: SimpleNamespace(stdout=json.dumps(payload), stderr=""),
        )

        result = make_runner()._run_jest(str(tmp_path))

        assert result.total == 3
        assert result.passed == 2
        assert result.failed == 1
        assert result.failures == [
            {"test": "suite fail", "reason": "expected true to be false"}
        ]

    def test_run_go_test_parses_pass_and_fail_counts(self, monkeypatch, tmp_path):
        output = "--- PASS: TestOne\n--- FAIL: TestTwo\n"
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *args, **kwargs: SimpleNamespace(stdout=output, stderr=""),
        )

        result = make_runner()._run_go_test(str(tmp_path))

        assert result.passed == 1
        assert result.failed == 1
        assert result.total == 2

    def test_run_cargo_test_parses_summary(self, monkeypatch, tmp_path):
        output = "test result: ok. 3 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out"
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *args, **kwargs: SimpleNamespace(stdout=output, stderr=""),
        )

        result = make_runner()._run_cargo_test(str(tmp_path))

        assert result.passed == 3
        assert result.failed == 1
        assert result.total == 4
