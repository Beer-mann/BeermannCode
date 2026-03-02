"""
Code analysis module for CodeAI Platform.
Analyzes code quality, complexity, and potential issues.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AnalysisResult:
    """Result of code analysis."""

    file_path: str
    language: str
    lines_of_code: int
    complexity_score: float
    issues: List[Dict]
    suggestions: List[str]
    quality_score: float
    ai_insights: str = ""

    def to_dict(self) -> Dict:
        """Convert result to dictionary."""
        return {
            "file_path": self.file_path,
            "language": self.language,
            "lines_of_code": self.lines_of_code,
            "complexity_score": self.complexity_score,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "quality_score": self.quality_score,
            "ai_insights": self.ai_insights,
        }


class CodeAnalyzer:
    """Analyzes code for quality, complexity, and potential issues."""

    def __init__(self, config):
        """Initialize code analyzer with configuration."""
        self.config = config
        self.supported_extensions = {
            "python": [".py"],
            "javascript": [".js", ".jsx", ".ts", ".tsx"],
            "java": [".java"],
            "cpp": [".cpp", ".h", ".hpp"],
            "csharp": [".cs"],
            "go": [".go"],
            "rust": [".rs"]
        }
        self.openai_client = config.get_openai_client()

    def analyze_file(self, file_path: str) -> Optional[AnalysisResult]:
        """
        Analyze a single code file.

        Args:
            file_path: Path to the code file

        Returns:
            AnalysisResult object with analysis details
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        language = self._detect_language(path)
        if not language:
            return None

        with open(path, 'r', encoding='utf-8') as f:
            code = f.read()

        lines_of_code = len([line for line in code.split('\n') if line.strip()])
        complexity_score = self._calculate_complexity(code, language)
        issues = self._detect_issues(code, language)
        suggestions = self._generate_suggestions(code, language, issues)
        quality_score = self._calculate_quality_score(complexity_score, issues)
        ai_insights = self._ai_analyze(code, language)

        return AnalysisResult(
            file_path=str(path),
            language=language,
            lines_of_code=lines_of_code,
            complexity_score=complexity_score,
            issues=issues,
            suggestions=suggestions,
            quality_score=quality_score,
            ai_insights=ai_insights,
        )

    def analyze_project(self, project_path: str) -> List[AnalysisResult]:
        """
        Analyze all code files in a project.

        Args:
            project_path: Path to the project directory

        Returns:
            List of AnalysisResult objects
        """
        results = []
        project = Path(project_path)

        if not project.exists():
            raise FileNotFoundError(f"Project path not found: {project_path}")

        for file_path in project.rglob("*"):
            if file_path.is_file():
                result = self.analyze_file(str(file_path))
                if result:
                    results.append(result)

        return results

    def _detect_language(self, path: Path) -> Optional[str]:
        """Detect programming language from file extension."""
        ext = path.suffix.lower()

        for language, extensions in self.supported_extensions.items():
            if language in self.config.supported_languages and ext in extensions:
                return language

        return None

    def _calculate_complexity(self, code: str, language: str) -> float:
        """Calculate code complexity score (0-100)."""
        lines = code.split('\n')

        loc_factor = min(len(lines) / 500, 1.0)

        max_indent = 0
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                max_indent = max(max_indent, indent)
        nesting_factor = min(max_indent / 40, 1.0)

        control_keywords = ['if', 'for', 'while', 'switch', 'case']
        control_count = sum(code.lower().count(keyword) for keyword in control_keywords)
        control_factor = min(control_count / 50, 1.0)

        complexity = (loc_factor * 0.3 + nesting_factor * 0.4 + control_factor * 0.3) * 100

        return round(complexity, 2)

    def _detect_issues(self, code: str, language: str) -> List[Dict]:
        """Detect potential code issues."""
        issues = []
        lines = code.split('\n')

        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                issues.append({
                    "line": i,
                    "type": "style",
                    "severity": "low",
                    "message": "Line exceeds 120 characters"
                })

        for i, line in enumerate(lines, 1):
            if 'TODO' in line or 'FIXME' in line:
                issues.append({
                    "line": i,
                    "type": "maintenance",
                    "severity": "info",
                    "message": "Unresolved TODO/FIXME comment"
                })

        if language == "python":
            if 'def ' in code and '"""' not in code and "'''" not in code:
                issues.append({
                    "line": None,
                    "type": "documentation",
                    "severity": "medium",
                    "message": "Functions missing docstrings"
                })

        return issues

    def _generate_suggestions(self, code: str, language: str, issues: List[Dict]) -> List[str]:
        """Generate improvement suggestions based on analysis."""
        suggestions = []

        high_severity_count = sum(1 for issue in issues if issue.get("severity") == "high")
        if high_severity_count > 0:
            suggestions.append(f"Address {high_severity_count} high-severity issues immediately")

        if language == "python":
            if 'import *' in code:
                suggestions.append("Avoid wildcard imports; use explicit imports")
            if code.count('def ') > 10:
                suggestions.append("Consider breaking down large files into smaller modules")

        if language == "javascript":
            if 'var ' in code:
                suggestions.append("Use 'let' or 'const' instead of 'var'")

        lines = code.split('\n')
        if len(lines) > 500:
            suggestions.append("Consider refactoring: file is very large")

        return suggestions

    def _calculate_quality_score(self, complexity: float, issues: List[Dict]) -> float:
        """Calculate overall quality score (0-100)."""
        score = 100.0

        score -= complexity * 0.3

        for issue in issues:
            severity = issue.get("severity", "low")
            if severity == "high":
                score -= 5
            elif severity == "medium":
                score -= 2
            else:
                score -= 0.5

        return max(0, round(score, 2))

    def _ai_analyze(self, code: str, language: str) -> str:
        """Use OpenAI to provide AI-powered code insights."""
        if not self.openai_client:
            return ""
        try:
            response = self.openai_client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are an expert {language} code analyst. "
                            "Analyze the code and provide 3-5 concise, actionable insights about "
                            "code quality, patterns, and improvements. Be specific and direct."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this {language} code:\n\n{code[:4000]}"
                    }
                ],
                max_tokens=600,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return ""
