"""
Code generation module for CodeAI Platform.
Generates code snippets, functions, and boilerplate code using OpenAI.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class GenerationRequest:
    """Request for code generation."""

    language: str
    description: str
    context: Optional[str] = None
    style: str = "clean"
    include_comments: bool = True
    include_tests: bool = False


@dataclass
class GenerationResult:
    """Result of code generation."""

    code: str
    language: str
    description: str
    includes_tests: bool
    metadata: Dict

    def to_dict(self) -> Dict:
        """Convert result to dictionary."""
        return {
            "code": self.code,
            "language": self.language,
            "description": self.description,
            "includes_tests": self.includes_tests,
            "metadata": self.metadata
        }


class CodeGenerator:
    """Generates code based on natural language descriptions."""

    def __init__(self, config):
        """Initialize code generator with configuration."""
        self.config = config
        self.templates = self._load_templates()
        self.openai_client = config.get_openai_client()

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """
        Generate code based on the request.

        Args:
            request: GenerationRequest with specifications

        Returns:
            GenerationResult with generated code
        """
        if request.language not in self.config.supported_languages:
            raise ValueError(f"Unsupported language: {request.language}")

        code = self._generate_code(request)

        if not self.openai_client and request.include_comments:
            code = self._add_comments(code, request.language, request.description)

        if not self.openai_client and request.include_tests:
            test_code = self._generate_tests(code, request.language)
            code = f"{code}\n\n{test_code}"

        metadata = {
            "style": request.style,
            "has_comments": request.include_comments,
            "has_tests": request.include_tests,
            "ai_powered": self.openai_client is not None,
        }

        return GenerationResult(
            code=code,
            language=request.language,
            description=request.description,
            includes_tests=request.include_tests,
            metadata=metadata
        )

    def generate_function(self, name: str, parameters: List[str],
                          return_type: str, language: str) -> str:
        """
        Generate a function signature and boilerplate.

        Args:
            name: Function name
            parameters: List of parameter names
            return_type: Return type
            language: Programming language

        Returns:
            Generated function code
        """
        if language == "python":
            params = ", ".join(parameters)
            code = f"def {name}({params}):\n"
            code += f'    """{name.replace("_", " ").title()}.\n    \n'
            code += f'    Args:\n'
            for param in parameters:
                code += f'        {param}: Description\n'
            code += f'    \n    Returns:\n'
            code += f'        {return_type}: Description\n'
            code += f'    """\n'
            code += f'    # TODO: Implement {name}\n'
            code += f'    pass\n'
            return code

        elif language == "javascript":
            params = ", ".join(parameters)
            code = f"/**\n * {name.replace('_', ' ').title()}\n"
            for param in parameters:
                code += f" * @param {{{return_type}}} {param} - Description\n"
            code += f" * @returns {{{return_type}}} Description\n"
            code += f" */\n"
            code += f"function {name}({params}) {{\n"
            code += f"  // TODO: Implement {name}\n"
            code += f"}}\n"
            return code

        elif language == "java":
            params = ", ".join([f"Object {p}" for p in parameters])
            code = f"/**\n * {name.replace('_', ' ').title()}\n"
            for param in parameters:
                code += f" * @param {param} Description\n"
            code += f" * @return {return_type} Description\n"
            code += f" */\n"
            code += f"public {return_type} {name}({params}) {{\n"
            code += f"    // TODO: Implement {name}\n"
            code += f"    return null;\n"
            code += f"}}\n"
            return code

        return f"// Function generation not supported for {language}"

    def generate_class(self, name: str, attributes: List[str],
                       methods: List[str], language: str) -> str:
        """
        Generate a class structure.

        Args:
            name: Class name
            attributes: List of attribute names
            methods: List of method names
            language: Programming language

        Returns:
            Generated class code
        """
        if language == "python":
            code = f"class {name}:\n"
            code += f'    """{name} class."""\n\n'
            code += f"    def __init__(self):\n"
            code += f'        """Initialize {name}."""\n'
            for attr in attributes:
                code += f"        self.{attr} = None\n"
            code += "\n"
            for method in methods:
                code += f"    def {method}(self):\n"
                code += f'        """{method.replace("_", " ").title()}."""\n'
                code += f"        pass\n\n"
            return code

        elif language == "javascript":
            code = f"class {name} {{\n"
            code += f"  constructor() {{\n"
            for attr in attributes:
                code += f"    this.{attr} = null;\n"
            code += f"  }}\n\n"
            for method in methods:
                code += f"  {method}() {{\n"
                code += f"    // TODO: Implement {method}\n"
                code += f"  }}\n\n"
            code += f"}}\n"
            return code

        elif language == "java":
            code = f"public class {name} {{\n"
            for attr in attributes:
                code += f"    private Object {attr};\n"
            code += f"\n    public {name}() {{\n"
            code += f"        // Constructor\n"
            code += f"    }}\n\n"
            for method in methods:
                code += f"    public void {method}() {{\n"
                code += f"        // TODO: Implement {method}\n"
                code += f"    }}\n\n"
            code += f"}}\n"
            return code

        return f"// Class generation not supported for {language}"

    def _load_templates(self) -> Dict:
        """Load code templates for different languages."""
        return {
            "python": {
                "function": "def {name}({params}):\n    pass\n",
                "class": "class {name}:\n    pass\n"
            },
            "javascript": {
                "function": "function {name}({params}) {{\n}}\n",
                "class": "class {name} {{\n}}\n"
            },
            "java": {
                "function": "public void {name}({params}) {{\n}}\n",
                "class": "public class {name} {{\n}}\n"
            }
        }

    def _generate_code(self, request: GenerationRequest) -> str:
        """Generate code using OpenAI if available, else fall back to templates."""
        if self.openai_client:
            return self._generate_with_ai(request)
        return self._generate_from_template(request)

    def _generate_with_ai(self, request: GenerationRequest) -> str:
        """Generate code using OpenAI gpt-4o-mini."""
        style_instruction = {
            "clean": "Write clean, readable, idiomatic code.",
            "verbose": "Write well-documented, verbose code with detailed comments.",
            "minimal": "Write minimal, concise code with no unnecessary boilerplate.",
        }.get(request.style, "Write clean, readable code.")

        test_instruction = " Include unit tests at the end." if request.include_tests else ""
        comment_instruction = " Add helpful inline comments." if request.include_comments else ""

        system_prompt = (
            f"You are an expert {request.language} programmer. "
            f"Generate only raw code without markdown code blocks or backticks. "
            f"{style_instruction}{comment_instruction}{test_instruction}"
        )

        user_prompt = f"Generate {request.language} code for: {request.description}"
        if request.context:
            user_prompt += f"\n\nContext:\n{request.context}"

        try:
            response = self.openai_client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"# AI generation failed: {e}\n" + self._generate_from_template(request)

    def _generate_from_template(self, request: GenerationRequest) -> str:
        """Fallback template-based code generation."""
        language = request.language
        description = request.description

        if "function" in description.lower():
            name = "generated_function"
            return self.generate_function(name, ["param1", "param2"], "Any", language)

        elif "class" in description.lower():
            name = "GeneratedClass"
            return self.generate_class(name, ["attribute1"], ["method1"], language)

        else:
            template = self.templates.get(language, {}).get("function", "")
            return template.format(name="generated_code", params="")

    def _add_comments(self, code: str, language: str, description: str) -> str:
        """Add comments to generated code."""
        if language == "python":
            return f'"""{description}"""\n\n{code}'
        elif language in ["javascript", "java"]:
            return f'/**\n * {description}\n */\n{code}'
        return code

    def _generate_tests(self, code: str, language: str) -> str:
        """Generate basic test structure."""
        if language == "python":
            return """
# Tests
def test_generated_code():
    '''Test generated code.'''
    assert True, "Test not implemented"
"""
        elif language == "javascript":
            return """
// Tests
describe('Generated Code', () => {
  it('should work', () => {
    // Test not implemented
  });
});
"""
        elif language == "java":
            return """
// Tests
@Test
public void testGeneratedCode() {
    // Test not implemented
}
"""
        return "// Tests not generated"
