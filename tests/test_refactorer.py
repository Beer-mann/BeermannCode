"""Tests for codeai_platform.modules.refactorer module."""

import pytest
from codeai_platform.config import CodeAIConfig
from codeai_platform.modules.refactorer import CodeRefactorer, RefactorSuggestion, RefactorResult


def make_config():
    config = CodeAIConfig()
    config.get_openai_client = lambda use_real=False: None
    return config


@pytest.fixture
def refactorer():
    return CodeRefactorer(make_config())


class TestRefactorSuggestionToDict:
    def test_to_dict_contains_expected_fields(self):
        s = RefactorSuggestion(
            file_path="foo.py",
            refactor_type="extract_method",
            severity="medium",
            description="Too long",
            line_start=1,
            line_end=60,
            confidence=0.8,
        )
        d = s.to_dict()
        assert d["file_path"] == "foo.py"
        assert d["refactor_type"] == "extract_method"
        assert d["severity"] == "medium"
        assert "1-60" in d["line_range"]
        assert d["confidence"] == 0.8


class TestRefactorResultToDict:
    def test_to_dict_structure(self):
        result = RefactorResult(
            file_path="foo.py",
            language="python",
            suggestions=[],
            code_smells=[],
            duplications=[],
            complexity_hotspots=[],
        )
        d = result.to_dict()
        assert d["file_path"] == "foo.py"
        assert d["language"] == "python"
        assert d["suggestions"] == []
        assert d["code_smells"] == []


class TestDetectLongMethods:
    def _make_long_function(self, name="big_func", lines=60):
        body = "\n".join([f"    x_{i} = {i}" for i in range(lines)])
        return f"def {name}():\n{body}\n"

    def test_detects_long_function(self, refactorer):
        code = self._make_long_function()
        suggestions = refactorer._detect_long_methods(code, "test.py", "python")
        assert len(suggestions) > 0
        assert suggestions[0].refactor_type == "extract_method"

    def test_short_function_not_flagged(self, refactorer):
        code = "def short():\n    return 1\n"
        suggestions = refactorer._detect_long_methods(code, "test.py", "python")
        assert len(suggestions) == 0

    def test_suggestion_includes_function_name(self, refactorer):
        code = self._make_long_function("my_func")
        suggestions = refactorer._detect_long_methods(code, "test.py", "python")
        assert any("my_func" in s.description for s in suggestions)

    def test_non_python_returns_empty(self, refactorer):
        code = "function big() {\n" + "\n".join([f"  var x{i} = {i};" for i in range(60)]) + "\n}"
        suggestions = refactorer._detect_long_methods(code, "test.js", "javascript")
        assert suggestions == []


class TestDetectDeepNesting:
    def test_deeply_nested_code_flagged(self, refactorer):
        code = (
            "def f():\n"
            "    if True:\n"
            "        for i in range(10):\n"
            "            if i > 5:\n"
            "                while True:\n"
            "                    if i:\n"
            "                        pass\n"
        )
        suggestions = refactorer._detect_deep_nesting(code, "test.py", "python")
        assert len(suggestions) > 0
        assert suggestions[0].refactor_type == "simplify"

    def test_shallow_nesting_not_flagged(self, refactorer):
        code = "def f():\n    if True:\n        return 1\n"
        suggestions = refactorer._detect_deep_nesting(code, "test.py", "python")
        assert suggestions == []


class TestDetectGodClass:
    def _make_big_class(self, method_count=20):
        methods = "\n".join([f"    def method_{i}(self):\n        pass" for i in range(method_count)])
        return f"class BigClass:\n{methods}\n"

    def test_god_class_detected(self, refactorer):
        code = self._make_big_class(20)
        suggestions = refactorer._detect_god_class(code, "test.py", "python")
        assert len(suggestions) > 0
        assert suggestions[0].refactor_type == "split_file"

    def test_small_class_not_flagged(self, refactorer):
        code = "class Small:\n    def method_a(self):\n        pass\n"
        suggestions = refactorer._detect_god_class(code, "test.py", "python")
        assert suggestions == []

    def test_non_python_returns_empty(self, refactorer):
        code = "class Foo { " + " ".join([f"method{i}() {{}}" for i in range(20)]) + " }"
        suggestions = refactorer._detect_god_class(code, "test.js", "javascript")
        assert suggestions == []


class TestDetectDeadCode:
    def test_commented_out_function_flagged(self, refactorer):
        code = "x = 1\n# def old_function():\n#     pass\n"
        suggestions = refactorer._detect_dead_code(code, "test.py", "python")
        assert len(suggestions) > 0

    def test_commented_out_import_flagged(self, refactorer):
        code = "# import os\nx = 1\n"
        suggestions = refactorer._detect_dead_code(code, "test.py", "python")
        assert len(suggestions) > 0

    def test_regular_comment_not_flagged(self, refactorer):
        code = "# This is a description\nx = 1\n"
        suggestions = refactorer._detect_dead_code(code, "test.py", "python")
        assert suggestions == []


class TestDetectSmells:
    def test_large_file_smell_detected(self, refactorer):
        code = "\n".join(["x = 1"] * 600)
        smells = refactorer._detect_smells(code, "python")
        assert any(s["type"] == "large_file" for s in smells)

    def test_import_bloat_detected(self, refactorer):
        imports = "\n".join([f"import module_{i}" for i in range(25)])
        smells = refactorer._detect_smells(imports, "python")
        assert any(s["type"] == "import_bloat" for s in smells)

    def test_clean_code_no_smells(self, refactorer):
        code = "def foo():\n    return 1\n"
        smells = refactorer._detect_smells(code, "python")
        assert smells == []


class TestDetectDuplications:
    def test_duplicate_blocks_detected(self, refactorer):
        block = "\n".join([f"line_{i} = {i}" for i in range(10)])
        code = block + "\n\n" + block
        duplications = refactorer._detect_duplications(code)
        assert len(duplications) > 0

    def test_unique_code_no_duplications(self, refactorer):
        code = "def foo():\n    return 1\ndef bar():\n    return 2\n"
        duplications = refactorer._detect_duplications(code)
        assert duplications == []

    def test_duplications_capped_at_10(self, refactorer):
        block = "x = 1\ny = 2\nz = 3\na = 4\nb = 5\n"
        code = (block * 30)
        duplications = refactorer._detect_duplications(code)
        assert len(duplications) <= 10


class TestAnalyzeFile:
    def test_analyze_file_returns_result(self, refactorer, tmp_path):
        f = tmp_path / "sample.py"
        f.write_text("def foo():\n    return 1\n")
        result = refactorer.analyze_file(str(f))
        assert isinstance(result, RefactorResult)
        assert result.language == "python"

    def test_analyze_file_not_found_raises(self, refactorer):
        with pytest.raises(FileNotFoundError):
            refactorer.analyze_file("/nonexistent/file.py")

    def test_analyze_file_returns_suggestions_list(self, refactorer, tmp_path):
        f = tmp_path / "sample.py"
        f.write_text("def foo():\n    return 1\n")
        result = refactorer.analyze_file(str(f))
        assert isinstance(result.suggestions, list)
        assert isinstance(result.code_smells, list)
        assert isinstance(result.duplications, list)
