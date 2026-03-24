"""Tests for CodeAnalyzer."""

import tempfile
import os
import pytest
from codeai_platform import CodeAIConfig, CodeAnalyzer


@pytest.fixture
def analyzer():
    config = CodeAIConfig(supported_languages=["python", "javascript"])
    return CodeAnalyzer(config)


def write_tmp(suffix, content):
    f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
    f.write(content)
    f.close()
    return f.name


class TestAnalyzeFile:
    def test_basic_python_analysis(self, analyzer):
        path = write_tmp(".py", "def foo():\n    pass\n")
        try:
            result = analyzer.analyze_file(path)
            assert result is not None
            assert result.language == "python"
            assert result.lines_of_code >= 1
            assert 0 <= result.quality_score <= 100
        finally:
            os.unlink(path)

    def test_unsupported_extension_returns_none(self, analyzer):
        path = write_tmp(".xyz", "some content")
        try:
            result = analyzer.analyze_file(path)
            assert result is None
        finally:
            os.unlink(path)

    def test_missing_file_raises(self, analyzer):
        with pytest.raises(FileNotFoundError):
            analyzer.analyze_file("/nonexistent/path/file.py")

    def test_long_lines_detected(self, analyzer):
        long_line = "x = " + "a" * 130
        path = write_tmp(".py", long_line + "\n")
        try:
            result = analyzer.analyze_file(path)
            assert any(issue["type"] == "style" for issue in result.issues)
        finally:
            os.unlink(path)

    def test_todo_comment_detected(self, analyzer):
        path = write_tmp(".py", "# TODO: fix this\nx = 1\n")
        try:
            result = analyzer.analyze_file(path)
            assert any(issue["type"] == "maintenance" for issue in result.issues)
        finally:
            os.unlink(path)


class TestAnalyzeProject:
    def test_skips_unreadable_files(self, analyzer, tmp_path):
        py_file = tmp_path / "ok.py"
        py_file.write_text("x = 1\n")
        bad_file = tmp_path / "bad.py"
        bad_file.write_bytes(b"\xff\xfe invalid utf-8 \xff")
        # Should not raise even with an unreadable/bad file
        results = analyzer.analyze_project(str(tmp_path))
        assert isinstance(results, list)

    def test_missing_project_raises(self, analyzer):
        with pytest.raises(FileNotFoundError):
            analyzer.analyze_project("/nonexistent/project")

    def test_returns_results_for_supported_files(self, analyzer, tmp_path):
        (tmp_path / "a.py").write_text("def f():\n    pass\n")
        (tmp_path / "b.js").write_text("function f() {}\n")
        (tmp_path / "c.txt").write_text("plain text")
        results = analyzer.analyze_project(str(tmp_path))
        assert len(results) == 2


class TestComplexity:
    def test_keyword_counting_no_substring_overcounting(self, analyzer):
        # 'elif' should not also count as 'if'
        code = "if x:\n    pass\nelif y:\n    pass\n"
        score_with_elif = analyzer._calculate_complexity(code, "python")
        # A line with 'before' should not count as a 'for' keyword
        code2 = "before = 1\n"
        score_no_for = analyzer._calculate_complexity(code2, "python")
        # 'before' contains 'for' as substring; with old code it would count
        assert analyzer._calculate_complexity("before = 1\n", "python") == \
               analyzer._calculate_complexity("x = 1\n", "python")
