"""Tests for CodeReviewer."""

import pytest
from codeai_platform import CodeAIConfig, CodeReviewer


@pytest.fixture
def reviewer():
    config = CodeAIConfig()
    return CodeReviewer(config)


class TestReviewCode:
    def test_returns_review_result(self, reviewer):
        result = reviewer.review_code("x = 1\n", "python")
        assert result.language == "python"
        assert result.overall_rating in ("excellent", "good", "fair", "poor")

    def test_detects_eval_usage(self, reviewer):
        result = reviewer.review_code("eval('1+1')\n", "python")
        categories = [c.category for c in result.comments]
        assert "security" in categories

    def test_no_false_positive_password_env(self, reviewer):
        """Assigning from os.getenv should NOT trigger hardcoded secret warning."""
        code = "import os\npassword = os.getenv('DB_PASSWORD')\n"
        result = reviewer.review_code(code, "python")
        security_msgs = [c.message for c in result.comments if c.category == "security"]
        assert not any("hardcoded" in m.lower() and "password" in m.lower()
                       for m in security_msgs)

    def test_detects_actual_hardcoded_password(self, reviewer):
        code = 'password = "s3cr3tP@ss"\n'
        result = reviewer.review_code(code, "python")
        security_msgs = [c.message for c in result.comments if c.category == "security"]
        assert any("password" in m.lower() for m in security_msgs)

    def test_no_false_positive_string_concat_no_loop(self, reviewer):
        """A += outside a loop should NOT trigger the string concat warning."""
        code = "result = ''\nresult += 'hello'\n"
        result = reviewer.review_code(code, "python")
        perf_msgs = [c.message for c in result.comments if c.category == "performance"]
        assert not any("string concatenation" in m.lower() for m in perf_msgs)

    def test_detects_string_concat_in_loop(self, reviewer):
        code = "s = ''\nfor i in range(10):\n    s += 'x'\n"
        result = reviewer.review_code(code, "python")
        perf_msgs = [c.message for c in result.comments if c.category == "performance"]
        assert any("string concatenation" in m.lower() for m in perf_msgs)

    def test_detects_trailing_whitespace(self, reviewer):
        result = reviewer.review_code("x = 1   \n", "python")
        style_msgs = [c.message for c in result.comments if c.category == "style"]
        assert any("trailing whitespace" in m.lower() for m in style_msgs)

    def test_detects_todo_comments(self, reviewer):
        result = reviewer.review_code("# TODO: fix me\nx = 1\n", "python")
        maint_msgs = [c.message for c in result.comments if c.category == "maintainability"]
        assert any("todo" in m.lower() for m in maint_msgs)


class TestRating:
    def test_excellent_for_clean_code(self, reviewer):
        result = reviewer.review_code("def add(a, b):\n    return a + b\n", "python")
        assert result.overall_rating in ("excellent", "good")

    def test_poor_for_eval(self, reviewer):
        result = reviewer.review_code("eval(input())\n", "python")
        assert result.overall_rating == "poor"
