"""Tests for codeai_platform.modules.analyzer module."""

import pytest
import tempfile
import os
from pathlib import Path
from codeai_platform.config import CodeAIConfig
from codeai_platform.modules.analyzer import CodeAnalyzer, AnalysisResult


def make_config():
    config = CodeAIConfig()
    config.get_openai_client = lambda use_real=False: None
    return config


@pytest.fixture
def analyzer():
    return CodeAnalyzer(make_config())


@pytest.fixture
def tmp_py_file(tmp_path):
    f = tmp_path / "sample.py"
    f.write_text("def add(a, b):\n    return a + b\n")
    return str(f)


class TestAnalysisResultToDict:
    def test_to_dict_contains_all_fields(self):
        result = AnalysisResult(
            file_path="foo.py",
            language="python",
            lines_of_code=10,
            complexity_score=5.0,
            issues=[],
            suggestions=[],
            quality_score=90.0,
        )
        d = result.to_dict()
        assert d["file_path"] == "foo.py"
        assert d["language"] == "python"
        assert d["lines_of_code"] == 10
        assert d["complexity_score"] == 5.0
        assert d["quality_score"] == 90.0


class TestDetectLanguage:
    def test_detects_python(self, analyzer, tmp_path):
        p = tmp_path / "main.py"
        assert analyzer._detect_language(p) == "python"

    def test_detects_javascript(self, analyzer, tmp_path):
        p = tmp_path / "app.js"
        assert analyzer._detect_language(p) == "javascript"

    def test_detects_typescript(self, analyzer, tmp_path):
        p = tmp_path / "app.ts"
        assert analyzer._detect_language(p) == "javascript"

    def test_detects_jsx(self, analyzer, tmp_path):
        p = tmp_path / "comp.jsx"
        assert analyzer._detect_language(p) == "javascript"

    def test_detects_java(self, analyzer, tmp_path):
        p = tmp_path / "Main.java"
        assert analyzer._detect_language(p) == "java"

    def test_detects_go(self, analyzer, tmp_path):
        p = tmp_path / "main.go"
        assert analyzer._detect_language(p) == "go"

    def test_detects_rust(self, analyzer, tmp_path):
        p = tmp_path / "lib.rs"
        assert analyzer._detect_language(p) == "rust"

    def test_unknown_extension_returns_none(self, analyzer, tmp_path):
        p = tmp_path / "file.xyz"
        assert analyzer._detect_language(p) is None

    def test_unsupported_language_not_in_config_returns_none(self, analyzer, tmp_path):
        config = make_config()
        config.supported_languages = ["python"]
        restricted_analyzer = CodeAnalyzer(config)
        p = tmp_path / "main.go"
        assert restricted_analyzer._detect_language(p) is None


class TestCalculateComplexity:
    def test_simple_code_low_complexity(self, analyzer):
        code = "x = 1\ny = 2\nz = x + y\n"
        score = analyzer._calculate_complexity(code, "python")
        assert 0 <= score <= 100

    def test_complexity_increases_with_control_flow(self, analyzer):
        simple = "x = 1\n"
        complex_code = "\n".join(["if x:" for _ in range(20)]) + "\n    pass\n"
        simple_score = analyzer._calculate_complexity(simple, "python")
        complex_score = analyzer._calculate_complexity(complex_code, "python")
        assert complex_score >= simple_score

    def test_complexity_score_in_valid_range(self, analyzer):
        code = "def f():\n    for i in range(10):\n        if i > 5:\n            pass\n"
        score = analyzer._calculate_complexity(code, "python")
        assert 0 <= score <= 100


class TestDetectIssues:
    def test_long_line_detected(self, analyzer):
        long_line = "x = " + "a" * 130
        issues = analyzer._detect_issues(long_line, "python")
        assert any(i["type"] == "style" for i in issues)

    def test_todo_comment_detected(self, analyzer):
        code = "# TODO: fix this\nx = 1\n"
        issues = analyzer._detect_issues(code, "python")
        assert any(i["type"] == "maintenance" for i in issues)

    def test_fixme_comment_detected(self, analyzer):
        code = "# FIXME: broken\nx = 1\n"
        issues = analyzer._detect_issues(code, "python")
        assert any(i["type"] == "maintenance" for i in issues)

    def test_missing_docstring_detected_for_python(self, analyzer):
        code = "def foo():\n    pass\n"
        issues = analyzer._detect_issues(code, "python")
        assert any(i["type"] == "documentation" for i in issues)

    def test_no_docstring_issue_for_javascript(self, analyzer):
        code = "function foo() { return 1; }"
        issues = analyzer._detect_issues(code, "javascript")
        assert not any(i["type"] == "documentation" for i in issues)

    def test_clean_code_has_no_issues(self, analyzer):
        code = '"""Module."""\n\ndef foo():\n    """Docstring."""\n    return 1\n'
        issues = analyzer._detect_issues(code, "python")
        assert issues == []


class TestGenerateSuggestions:
    def test_wildcard_import_suggestion(self, analyzer):
        code = "from os import *\n"
        suggestions = analyzer._generate_suggestions(code, "python", [])
        assert any("wildcard" in s.lower() or "import *" in s for s in suggestions)

    def test_many_functions_suggestion(self, analyzer):
        code = "def f{}(): pass\n".join(str(i) for i in range(12))
        # Build a string with >10 def statements
        code = "\n".join([f"def func_{i}(): pass" for i in range(12)])
        suggestions = analyzer._generate_suggestions(code, "python", [])
        assert any("module" in s.lower() or "large" in s.lower() or "breaking" in s.lower() for s in suggestions)

    def test_var_usage_suggestion_for_javascript(self, analyzer):
        code = "var x = 1;\n"
        suggestions = analyzer._generate_suggestions(code, "javascript", [])
        assert any("var" in s.lower() or "let" in s.lower() or "const" in s.lower() for s in suggestions)

    def test_high_severity_issue_triggers_suggestion(self, analyzer):
        issues = [{"severity": "high", "type": "security", "message": "issue"}]
        suggestions = analyzer._generate_suggestions("x=1", "python", issues)
        assert any("high" in s.lower() or "critical" in s.lower() or "high-severity" in s.lower() for s in suggestions)


class TestCalculateQualityScore:
    def test_perfect_code_has_high_score(self, analyzer):
        score = analyzer._calculate_quality_score(0, [])
        assert score == 100.0

    def test_high_severity_reduces_score(self, analyzer):
        no_issues = analyzer._calculate_quality_score(0, [])
        with_issue = analyzer._calculate_quality_score(0, [{"severity": "high"}])
        assert with_issue < no_issues

    def test_score_never_below_zero(self, analyzer):
        issues = [{"severity": "high"}] * 100
        score = analyzer._calculate_quality_score(100, issues)
        assert score >= 0


class TestAnalyzeFile:
    def test_analyze_python_file(self, analyzer, tmp_py_file):
        result = analyzer.analyze_file(tmp_py_file)
        assert result is not None
        assert isinstance(result, AnalysisResult)
        assert result.language == "python"
        assert result.lines_of_code > 0
        assert 0 <= result.quality_score <= 100

    def test_analyze_file_not_found_raises(self, analyzer):
        with pytest.raises(FileNotFoundError):
            analyzer.analyze_file("/nonexistent/path/file.py")

    def test_analyze_unsupported_extension_returns_none(self, analyzer, tmp_path):
        f = tmp_path / "file.xyz"
        f.write_text("some content")
        result = analyzer.analyze_file(str(f))
        assert result is None

    def test_analyze_file_returns_correct_path(self, analyzer, tmp_py_file):
        result = analyzer.analyze_file(tmp_py_file)
        assert result.file_path == tmp_py_file

    def test_analyze_counts_lines_of_code(self, analyzer, tmp_path):
        f = tmp_path / "multi.py"
        f.write_text("x = 1\ny = 2\nz = 3\n")
        result = analyzer.analyze_file(str(f))
        assert result.lines_of_code == 3


class TestAnalyzeProject:
    def test_analyze_project_not_found_raises(self, analyzer):
        with pytest.raises(FileNotFoundError):
            analyzer.analyze_project("/nonexistent/project")

    def test_analyze_project_returns_list(self, analyzer, tmp_path):
        py_file = tmp_path / "main.py"
        py_file.write_text("x = 1\n")
        results = analyzer.analyze_project(str(tmp_path))
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_analyze_project_skips_unsupported_files(self, analyzer, tmp_path):
        (tmp_path / "readme.txt").write_text("hello")
        (tmp_path / "main.py").write_text("x = 1\n")
        results = analyzer.analyze_project(str(tmp_path))
        paths = [r.file_path for r in results]
        assert not any("readme.txt" in p for p in paths)
