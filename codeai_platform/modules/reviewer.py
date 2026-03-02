"""
Code review module for CodeAI Platform.
Provides automated code review and improvement suggestions.
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ReviewComment:
    """A single review comment."""

    line_number: Optional[int]
    severity: str  # info, warning, critical
    category: str  # style, performance, security, maintainability
    message: str
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert comment to dictionary."""
        return {
            "line_number": self.line_number,
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "suggestion": self.suggestion
        }


@dataclass
class ReviewResult:
    """Result of code review."""

    file_path: str
    language: str
    overall_rating: str  # excellent, good, fair, poor
    comments: List[ReviewComment]
    summary: str
    metrics: Dict
    ai_review: str = ""

    def to_dict(self) -> Dict:
        """Convert result to dictionary."""
        return {
            "file_path": self.file_path,
            "language": self.language,
            "overall_rating": self.overall_rating,
            "comments": [c.to_dict() for c in self.comments],
            "summary": self.summary,
            "metrics": self.metrics,
            "ai_review": self.ai_review,
        }


class CodeReviewer:
    """Performs automated code reviews."""

    def __init__(self, config):
        """Initialize code reviewer with configuration."""
        self.config = config
        self.review_rules = self._load_review_rules()
        self.openai_client = None
        try:
            from openai import OpenAI
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
        except ImportError:
            pass

    def review_file(self, file_path: str) -> ReviewResult:
        """
        Review a single code file.

        Args:
            file_path: Path to the code file

        Returns:
            ReviewResult with review findings
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        language = self._detect_language(path)
        if not language:
            raise ValueError(f"Unsupported file type: {path.suffix}")

        with open(path, 'r', encoding='utf-8') as f:
            code = f.read()

        comments = self._analyze_code(code, language)
        metrics = self._calculate_metrics(code, comments)
        overall_rating = self._calculate_rating(metrics, comments)
        summary = self._generate_summary(comments, metrics)
        ai_review = self._ai_review(code, language)

        return ReviewResult(
            file_path=str(path),
            language=language,
            overall_rating=overall_rating,
            comments=comments,
            summary=summary,
            metrics=metrics,
            ai_review=ai_review,
        )

    def review_code(self, code: str, language: str) -> ReviewResult:
        """
        Review code string directly.

        Args:
            code: Code string to review
            language: Programming language

        Returns:
            ReviewResult with review findings
        """
        comments = self._analyze_code(code, language)
        metrics = self._calculate_metrics(code, comments)
        overall_rating = self._calculate_rating(metrics, comments)
        summary = self._generate_summary(comments, metrics)
        ai_review = self._ai_review(code, language)

        return ReviewResult(
            file_path="<string>",
            language=language,
            overall_rating=overall_rating,
            comments=comments,
            summary=summary,
            metrics=metrics,
            ai_review=ai_review,
        )

    def _load_review_rules(self) -> Dict:
        """Load review rules for different categories."""
        return {
            "style": {
                "max_line_length": 120,
                "naming_convention": True,
                "indentation": True
            },
            "performance": {
                "check_loops": True,
                "check_recursion": True,
                "check_memory": True
            },
            "security": {
                "check_injection": True,
                "check_hardcoded_secrets": True,
                "check_unsafe_functions": True
            },
            "maintainability": {
                "check_complexity": True,
                "check_duplication": True,
                "check_documentation": True
            }
        }

    def _detect_language(self, path: Path) -> Optional[str]:
        """Detect programming language from file extension."""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "javascript",
            ".tsx": "javascript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "cpp",
            ".h": "cpp",
            ".cs": "csharp",
            ".go": "go",
            ".rs": "rust"
        }
        return ext_map.get(path.suffix.lower())

    def _analyze_code(self, code: str, language: str) -> List[ReviewComment]:
        """Analyze code and generate review comments."""
        comments = []
        lines = code.split('\n')

        comments.extend(self._check_style(lines, language))
        comments.extend(self._check_performance(code, language))
        comments.extend(self._check_security(code, language))
        comments.extend(self._check_maintainability(code, language))

        return comments

    def _check_style(self, lines: List[str], language: str) -> List[ReviewComment]:
        """Check code style issues."""
        comments = []

        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                comments.append(ReviewComment(
                    line_number=i,
                    severity="warning",
                    category="style",
                    message=f"Line exceeds 120 characters (length: {len(line)})",
                    suggestion="Break long lines into multiple lines"
                ))

            if line.rstrip() != line:
                comments.append(ReviewComment(
                    line_number=i,
                    severity="info",
                    category="style",
                    message="Line has trailing whitespace",
                    suggestion="Remove trailing whitespace"
                ))

        if language == "python":
            code = '\n'.join(lines)
            if '\t' in code:
                comments.append(ReviewComment(
                    line_number=None,
                    severity="warning",
                    category="style",
                    message="Code uses tabs instead of spaces",
                    suggestion="Use 4 spaces for indentation"
                ))

        return comments

    def _check_performance(self, code: str, language: str) -> List[ReviewComment]:
        """Check performance issues."""
        comments = []

        if language == "python":
            nested_loops = code.count("for") + code.count("while")
            if nested_loops > 3:
                comments.append(ReviewComment(
                    line_number=None,
                    severity="info",
                    category="performance",
                    message=f"Multiple nested loops detected ({nested_loops})",
                    suggestion="Consider optimizing nested loops or using more efficient algorithms"
                ))

        if "+=" in code and ("for " in code or "while " in code):
            comments.append(ReviewComment(
                line_number=None,
                severity="warning",
                category="performance",
                message="String concatenation in loop detected",
                suggestion="Consider using join() or list comprehension for better performance"
            ))

        return comments

    def _check_security(self, code: str, language: str) -> List[ReviewComment]:
        """Check security issues."""
        comments = []

        if "execute(" in code or "query(" in code:
            if "+" in code or "%" in code:
                comments.append(ReviewComment(
                    line_number=None,
                    severity="critical",
                    category="security",
                    message="Potential SQL injection vulnerability",
                    suggestion="Use parameterized queries or prepared statements"
                ))

        sensitive_keywords = ["password", "api_key", "secret", "token"]
        code_lower = code.lower()
        for keyword in sensitive_keywords:
            if f'{keyword}=' in code_lower or f'{keyword} =' in code_lower:
                comments.append(ReviewComment(
                    line_number=None,
                    severity="critical",
                    category="security",
                    message=f"Possible hardcoded {keyword} detected",
                    suggestion="Store secrets in environment variables or secure vaults"
                ))

        if "eval(" in code:
            comments.append(ReviewComment(
                line_number=None,
                severity="critical",
                category="security",
                message="Use of eval() detected",
                suggestion="Avoid eval() as it can execute arbitrary code"
            ))

        return comments

    def _check_maintainability(self, code: str, language: str) -> List[ReviewComment]:
        """Check maintainability issues."""
        comments = []
        lines = code.split('\n')

        if len(lines) > 500:
            comments.append(ReviewComment(
                line_number=None,
                severity="warning",
                category="maintainability",
                message=f"File is very long ({len(lines)} lines)",
                suggestion="Consider splitting into smaller modules"
            ))

        import re
        numbers = re.findall(r'\b\d{3,}\b', code)
        if len(numbers) > 5:
            comments.append(ReviewComment(
                line_number=None,
                severity="info",
                category="maintainability",
                message="Multiple magic numbers detected",
                suggestion="Extract magic numbers to named constants"
            ))

        for i, line in enumerate(lines, 1):
            if "TODO" in line or "FIXME" in line:
                comments.append(ReviewComment(
                    line_number=i,
                    severity="info",
                    category="maintainability",
                    message="Unresolved TODO/FIXME comment",
                    suggestion="Address or document the TODO/FIXME item"
                ))

        return comments

    def _calculate_metrics(self, code: str, comments: List[ReviewComment]) -> Dict:
        """Calculate code metrics."""
        lines = code.split('\n')

        return {
            "total_lines": len(lines),
            "code_lines": len([l for l in lines if l.strip()]),
            "comment_lines": len([l for l in lines if l.strip().startswith('#') or l.strip().startswith('//')]),
            "total_issues": len(comments),
            "critical_issues": sum(1 for c in comments if c.severity == "critical"),
            "warnings": sum(1 for c in comments if c.severity == "warning"),
            "info_issues": sum(1 for c in comments if c.severity == "info")
        }

    def _calculate_rating(self, metrics: Dict, comments: List[ReviewComment]) -> str:
        """Calculate overall rating."""
        critical = metrics["critical_issues"]
        warnings = metrics["warnings"]

        if critical > 0:
            return "poor"
        elif warnings > 5:
            return "fair"
        elif warnings > 0:
            return "good"
        else:
            return "excellent"

    def _generate_summary(self, comments: List[ReviewComment], metrics: Dict) -> str:
        """Generate review summary."""
        rating = self._calculate_rating(metrics, comments)

        summary = f"Code review complete. Overall rating: {rating.upper()}\n\n"
        summary += f"Total issues found: {metrics['total_issues']}\n"
        summary += f"- Critical: {metrics['critical_issues']}\n"
        summary += f"- Warnings: {metrics['warnings']}\n"
        summary += f"- Info: {metrics['info_issues']}\n\n"

        if metrics['critical_issues'] > 0:
            summary += "Critical issues must be addressed immediately.\n"
        elif metrics['warnings'] > 0:
            summary += "No critical issues, but some warnings need attention.\n"
        else:
            summary += "Code looks good! Minor improvements suggested.\n"

        return summary

    def _ai_review(self, code: str, language: str) -> str:
        """Use OpenAI to provide a comprehensive AI-powered code review."""
        if not self.openai_client:
            return ""
        try:
            response = self.openai_client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are a senior {language} engineer doing a thorough code review. "
                            "Identify bugs, bad patterns, security issues, and concrete improvements. "
                            "Be direct and specific. Format your review with clear sections."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Review this {language} code:\n\n{code[:4000]}"
                    }
                ],
                max_tokens=800,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return ""
