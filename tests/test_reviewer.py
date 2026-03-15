"""Tests for codeai_platform.modules.reviewer module."""

import pytest
from codeai_platform.config import CodeAIConfig
from codeai_platform.modules.reviewer import CodeReviewer, ReviewComment, ReviewResult


def make_config():
    config = CodeAIConfig()
    config.get_openai_client = lambda use_real=False: None
    return config


@pytest.fixture
def reviewer():
    return CodeReviewer(make_config())


class TestReviewCommentToDict:
    def test_to_dict_contains_all_fields(self):
        comment = ReviewComment(
            line_number=5,
            severity="warning",
            category="style",
            message="Line too long",
            suggestion="Break it up",
        )
        d = comment.to_dict()
        assert d["line_number"] == 5
        assert d["severity"] == "warning"
        assert d["category"] == "style"
        assert d["message"] == "Line too long"
        assert d["suggestion"] == "Break it up"

    def test_to_dict_optional_suggestion_none(self):
        comment = ReviewComment(line_number=None, severity="info", category="style", message="msg")
        assert comment.to_dict()["suggestion"] is None


class TestReviewResultToDict:
    def test_to_dict_structure(self):
        result = ReviewResult(
            file_path="foo.py",
            language="python",
            overall_rating="good",
            comments=[],
            summary="ok",
            metrics={},
        )
        d = result.to_dict()
        assert d["file_path"] == "foo.py"
        assert d["overall_rating"] == "good"
        assert d["comments"] == []


class TestCheckStyle:
    def test_long_line_flagged(self, reviewer):
        lines = ["x" * 130]
        comments = reviewer._check_style(lines, "python")
        assert any(c.category == "style" and "120" in c.message for c in comments)

    def test_trailing_whitespace_flagged(self, reviewer):
        lines = ["x = 1   "]
        comments = reviewer._check_style(lines, "python")
        assert any("trailing whitespace" in c.message.lower() for c in comments)

    def test_tabs_flagged_for_python(self, reviewer):
        lines = ["\tdef foo():", "\t\treturn 1"]
        comments = reviewer._check_style(lines, "python")
        assert any("tab" in c.message.lower() for c in comments)

    def test_clean_code_no_style_issues(self, reviewer):
        lines = ["def foo():", "    return 1"]
        comments = reviewer._check_style(lines, "python")
        assert all(c.category != "style" for c in comments)


class TestCheckPerformance:
    def test_string_concat_in_loop_flagged(self, reviewer):
        code = "result = ''\nfor i in range(10):\n    result += str(i)\n"
        comments = reviewer._check_performance(code, "python")
        assert any("concatenation" in c.message.lower() for c in comments)

    def test_many_loops_flagged(self, reviewer):
        code = "\n".join(["for i in range(10):" for _ in range(5)]) + "\n    pass"
        comments = reviewer._check_performance(code, "python")
        assert any(c.category == "performance" for c in comments)

    def test_clean_code_no_performance_issues(self, reviewer):
        code = "x = sum(range(10))\n"
        comments = reviewer._check_performance(code, "python")
        assert comments == []


class TestCheckSecurity:
    def test_sql_injection_via_concat_flagged(self, reviewer):
        code = 'query = "SELECT * FROM users WHERE id = " + user_id\nexecute(query)\n'
        comments = reviewer._check_security(code, "python")
        assert any("sql" in c.message.lower() or "injection" in c.message.lower() for c in comments)

    def test_hardcoded_password_flagged(self, reviewer):
        code = "password = 'supersecret'\n"
        comments = reviewer._check_security(code, "python")
        assert any("password" in c.message.lower() for c in comments)

    def test_hardcoded_api_key_flagged(self, reviewer):
        code = "api_key = 'abc123'\n"
        comments = reviewer._check_security(code, "python")
        assert any("api_key" in c.message.lower() for c in comments)

    def test_eval_usage_flagged(self, reviewer):
        code = "result = eval(user_input)\n"
        comments = reviewer._check_security(code, "python")
        assert any("eval" in c.message.lower() for c in comments)

    def test_eval_severity_is_critical(self, reviewer):
        code = "result = eval(user_input)\n"
        comments = reviewer._check_security(code, "python")
        eval_comments = [c for c in comments if "eval" in c.message.lower()]
        assert eval_comments[0].severity == "critical"

    def test_clean_code_no_security_issues(self, reviewer):
        code = "def add(a, b):\n    return a + b\n"
        comments = reviewer._check_security(code, "python")
        assert comments == []


class TestCheckMaintainability:
    def test_long_file_flagged(self, reviewer):
        code = "\n".join(["x = 1"] * 600)
        comments = reviewer._check_maintainability(code, "python")
        assert any(c.category == "maintainability" and "long" in c.message.lower() for c in comments)

    def test_todo_flagged(self, reviewer):
        code = "# TODO: implement this\nx = 1\n"
        comments = reviewer._check_maintainability(code, "python")
        assert any("todo" in c.message.lower() or "fixme" in c.message.lower() for c in comments)

    def test_magic_numbers_flagged(self, reviewer):
        code = "x = 12345\ny = 67890\nz = 11111\na = 22222\nb = 33333\nc = 44444\n"
        comments = reviewer._check_maintainability(code, "python")
        assert any("magic" in c.message.lower() for c in comments)

    def test_clean_code_no_maintainability_issues(self, reviewer):
        code = "MAX = 10\n\ndef process(n):\n    return n * MAX\n"
        comments = reviewer._check_maintainability(code, "python")
        assert not any(c.category == "maintainability" for c in comments)


class TestCalculateRating:
    def test_critical_issue_gives_poor_rating(self, reviewer):
        metrics = {"critical_issues": 1, "warnings": 0}
        comments = [ReviewComment(None, "critical", "security", "bad")]
        assert reviewer._calculate_rating(metrics, comments) == "poor"

    def test_many_warnings_gives_fair_rating(self, reviewer):
        metrics = {"critical_issues": 0, "warnings": 6}
        assert reviewer._calculate_rating(metrics, []) == "fair"

    def test_few_warnings_gives_good_rating(self, reviewer):
        metrics = {"critical_issues": 0, "warnings": 3}
        assert reviewer._calculate_rating(metrics, []) == "good"

    def test_no_issues_gives_excellent_rating(self, reviewer):
        metrics = {"critical_issues": 0, "warnings": 0}
        assert reviewer._calculate_rating(metrics, []) == "excellent"


class TestCalculateMetrics:
    def test_counts_total_lines(self, reviewer):
        code = "line1\nline2\nline3"
        metrics = reviewer._calculate_metrics(code, [])
        assert metrics["total_lines"] == 3

    def test_counts_comment_lines(self, reviewer):
        code = "# comment\nx = 1\n# another\n"
        metrics = reviewer._calculate_metrics(code, [])
        assert metrics["comment_lines"] == 2

    def test_counts_issues_by_severity(self, reviewer):
        comments = [
            ReviewComment(None, "critical", "security", "c1"),
            ReviewComment(None, "warning", "style", "w1"),
            ReviewComment(None, "info", "maintainability", "i1"),
        ]
        metrics = reviewer._calculate_metrics("x=1", comments)
        assert metrics["critical_issues"] == 1
        assert metrics["warnings"] == 1
        assert metrics["info_issues"] == 1


class TestReviewCode:
    def test_review_code_returns_result(self, reviewer):
        result = reviewer.review_code("def add(a, b):\n    return a + b\n", "python")
        assert isinstance(result, ReviewResult)
        assert result.language == "python"
        assert result.file_path == "<string>"

    def test_review_code_has_overall_rating(self, reviewer):
        result = reviewer.review_code("x = 1\n", "python")
        assert result.overall_rating in ("excellent", "good", "fair", "poor")

    def test_review_code_with_issues_finds_them(self, reviewer):
        code = "password = 'hardcoded'\n"
        result = reviewer.review_code(code, "python")
        assert len(result.comments) > 0

    def test_review_file_not_found_raises(self, reviewer):
        with pytest.raises(FileNotFoundError):
            reviewer.review_file("/nonexistent/path/file.py")

    def test_review_file_unsupported_extension_raises(self, reviewer, tmp_path):
        f = tmp_path / "file.xyz"
        f.write_text("content")
        with pytest.raises(ValueError):
            reviewer.review_file(str(f))

    def test_review_file_python(self, reviewer, tmp_path):
        f = tmp_path / "sample.py"
        f.write_text("def foo():\n    return 1\n")
        result = reviewer.review_file(str(f))
        assert result.language == "python"
        assert isinstance(result.metrics, dict)
