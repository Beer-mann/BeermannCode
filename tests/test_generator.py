"""Tests for CodeGenerator."""

import pytest
from codeai_platform import CodeAIConfig, CodeGenerator
from codeai_platform.generator import GenerationRequest


@pytest.fixture
def generator():
    return CodeGenerator(CodeAIConfig())


class TestGenerateFunction:
    def test_python_function(self, generator):
        code = generator.generate_function("my_func", ["a", "b"], "int", "python")
        assert "def my_func(a, b):" in code
        assert '"""' in code

    def test_javascript_function(self, generator):
        code = generator.generate_function("myFunc", ["x"], "string", "javascript")
        assert "function myFunc(x)" in code
        assert "@param {*} x" in code
        assert "@returns {string}" in code

    def test_java_function(self, generator):
        code = generator.generate_function("myMethod", ["val"], "void", "java")
        assert "public void myMethod" in code

    def test_unsupported_language_returns_comment(self, generator):
        code = generator.generate_function("f", [], "void", "cobol")
        assert "not supported" in code.lower()


class TestGenerateClass:
    def test_python_class(self, generator):
        code = generator.generate_class("MyClass", ["attr1"], ["method1"], "python")
        assert "class MyClass:" in code
        assert "self.attr1" in code
        assert "def method1" in code

    def test_javascript_class(self, generator):
        code = generator.generate_class("MyClass", ["x"], ["doIt"], "javascript")
        assert "class MyClass" in code
        assert "this.x" in code
        assert "doIt()" in code

    def test_java_class(self, generator):
        code = generator.generate_class("MyBean", ["name"], ["getName"], "java")
        assert "public class MyBean" in code
        assert "private Object name" in code


class TestGenerate:
    def test_unsupported_language_raises(self, generator):
        req = GenerationRequest(language="cobol", description="do something")
        with pytest.raises(ValueError, match="Unsupported language"):
            generator.generate(req)

    def test_generates_python_code(self, generator):
        req = GenerationRequest(language="python", description="create a function")
        result = generator.generate(req)
        assert result.language == "python"
        assert result.code
