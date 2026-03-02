"""
Code refactoring module for CodeAI Platform.
Detects code smells, duplications, and suggests/applies refactorings.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import re
import hashlib


@dataclass
class RefactorSuggestion:
    """A suggested refactoring."""
    file_path: str
    refactor_type: str  # extract_method, rename, simplify, deduplicate, split_file
    severity: str  # low, medium, high
    description: str
    original_code: str = ""
    suggested_code: str = ""
    line_start: int = 0
    line_end: int = 0
    confidence: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "file_path": self.file_path,
            "refactor_type": self.refactor_type,
            "severity": self.severity,
            "description": self.description,
            "line_range": f"{self.line_start}-{self.line_end}",
            "confidence": self.confidence,
        }


@dataclass
class RefactorResult:
    """Result of refactoring analysis."""
    file_path: str
    language: str
    suggestions: List[RefactorSuggestion]
    code_smells: List[Dict]
    duplications: List[Dict]
    complexity_hotspots: List[Dict]
    ai_suggestions: str = ""

    def to_dict(self) -> Dict:
        return {
            "file_path": self.file_path,
            "language": self.language,
            "suggestions": [s.to_dict() for s in self.suggestions],
            "code_smells": self.code_smells,
            "duplications": self.duplications,
            "complexity_hotspots": self.complexity_hotspots,
            "ai_suggestions": self.ai_suggestions,
        }


class CodeRefactorer:
    """Detects code smells and suggests refactorings."""

    def __init__(self, config):
        self.config = config
        self.openai_client = config.get_openai_client()

    def analyze_file(self, file_path: str) -> RefactorResult:
        """Analyze a file for refactoring opportunities."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        code = path.read_text(encoding="utf-8", errors="ignore")
        language = self._detect_language(path)

        suggestions = []
        suggestions.extend(self._detect_long_methods(code, file_path, language))
        suggestions.extend(self._detect_deep_nesting(code, file_path, language))
        suggestions.extend(self._detect_god_class(code, file_path, language))
        suggestions.extend(self._detect_dead_code(code, file_path, language))

        code_smells = self._detect_smells(code, language)
        duplications = self._detect_duplications(code)
        hotspots = self._find_complexity_hotspots(code, language)
        ai_suggestions = self._ai_refactor(code, language)

        return RefactorResult(
            file_path=file_path,
            language=language or "unknown",
            suggestions=suggestions,
            code_smells=code_smells,
            duplications=duplications,
            complexity_hotspots=hotspots,
            ai_suggestions=ai_suggestions,
        )

    def analyze_project(self, project_path: str) -> List[RefactorResult]:
        """Analyze entire project for refactoring opportunities."""
        results = []
        project = Path(project_path)
        ignore = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
        exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs"}

        for file_path in project.rglob("*"):
            if file_path.is_file() and file_path.suffix in exts:
                if not any(p in ignore for p in file_path.parts):
                    try:
                        results.append(self.analyze_file(str(file_path)))
                    except Exception:
                        continue
        return results

    def refactor_with_ai(self, code: str, language: str, instruction: str) -> str:
        """Use AI to apply a specific refactoring."""
        if not self.openai_client:
            return code

        try:
            response = self.openai_client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are an expert {language} refactoring assistant. "
                            "Apply the requested refactoring. Return ONLY the refactored code, "
                            "no explanations or markdown."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Refactoring: {instruction}\n\nCode:\n{code[:6000]}",
                    },
                ],
                max_tokens=self.config.max_tokens,
                temperature=0.1,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return code

    def _detect_long_methods(self, code: str, file_path: str, language: str) -> List[RefactorSuggestion]:
        """Detect methods/functions that are too long."""
        suggestions = []
        lines = code.split("\n")
        threshold = 50  # lines

        if language == "python":
            current_func = None
            func_start = 0
            func_indent = 0

            for i, line in enumerate(lines):
                match = re.match(r"^(\s*)def\s+(\w+)", line)
                if match:
                    if current_func and (i - func_start) > threshold:
                        suggestions.append(RefactorSuggestion(
                            file_path=file_path,
                            refactor_type="extract_method",
                            severity="medium",
                            description=f"Function '{current_func}' is {i - func_start} lines long. Consider splitting.",
                            line_start=func_start + 1,
                            line_end=i,
                            confidence=0.8,
                        ))
                    current_func = match.group(2)
                    func_start = i
                    func_indent = len(match.group(1))

            # Check last function
            if current_func and (len(lines) - func_start) > threshold:
                suggestions.append(RefactorSuggestion(
                    file_path=file_path,
                    refactor_type="extract_method",
                    severity="medium",
                    description=f"Function '{current_func}' is {len(lines) - func_start} lines long.",
                    line_start=func_start + 1,
                    line_end=len(lines),
                    confidence=0.8,
                ))

        return suggestions

    def _detect_deep_nesting(self, code: str, file_path: str, language: str) -> List[RefactorSuggestion]:
        """Detect deeply nested code blocks."""
        suggestions = []
        lines = code.split("\n")
        max_depth = 4 if language == "python" else 5

        for i, line in enumerate(lines):
            if not line.strip():
                continue
            indent = len(line) - len(line.lstrip())
            depth = indent // 4 if language == "python" else indent // 2

            if depth >= max_depth:
                suggestions.append(RefactorSuggestion(
                    file_path=file_path,
                    refactor_type="simplify",
                    severity="medium",
                    description=f"Deep nesting (level {depth}) at line {i+1}. Consider early returns or extraction.",
                    line_start=i + 1,
                    line_end=i + 1,
                    confidence=0.7,
                ))
                break  # Only report once per file

        return suggestions

    def _detect_god_class(self, code: str, file_path: str, language: str) -> List[RefactorSuggestion]:
        """Detect classes with too many methods/attributes."""
        suggestions = []
        if language != "python":
            return suggestions

        classes = re.findall(r"^class\s+(\w+)", code, re.MULTILINE)
        for cls_name in classes:
            # Count methods in class
            pattern = rf"class\s+{cls_name}.*?(?=\nclass\s|\Z)"
            match = re.search(pattern, code, re.DOTALL)
            if match:
                class_code = match.group()
                method_count = len(re.findall(r"\s+def\s+", class_code))
                if method_count > 15:
                    suggestions.append(RefactorSuggestion(
                        file_path=file_path,
                        refactor_type="split_file",
                        severity="high",
                        description=f"Class '{cls_name}' has {method_count} methods. Consider splitting into smaller classes.",
                        confidence=0.85,
                    ))

        return suggestions

    def _detect_dead_code(self, code: str, file_path: str, language: str) -> List[RefactorSuggestion]:
        """Basic dead code detection."""
        suggestions = []
        lines = code.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()
            # Commented-out code blocks
            if language == "python" and stripped.startswith("#") and any(
                kw in stripped for kw in ["def ", "class ", "import ", "return ", "if ", "for "]
            ):
                suggestions.append(RefactorSuggestion(
                    file_path=file_path,
                    refactor_type="simplify",
                    severity="low",
                    description=f"Commented-out code at line {i+1}. Remove if not needed.",
                    line_start=i + 1,
                    line_end=i + 1,
                    confidence=0.5,
                ))

        return suggestions

    def _detect_smells(self, code: str, language: str) -> List[Dict]:
        """Detect common code smells."""
        smells = []

        # Large file
        lines = len(code.split("\n"))
        if lines > 500:
            smells.append({"type": "large_file", "severity": "medium", "detail": f"{lines} lines"})

        # Too many imports
        if language == "python":
            imports = len(re.findall(r"^(?:import|from)\s+", code, re.MULTILINE))
            if imports > 20:
                smells.append({"type": "import_bloat", "severity": "low", "detail": f"{imports} imports"})

            # Global variables
            globals_found = re.findall(r"^[A-Z_]+\s*=", code, re.MULTILINE)
            if len(globals_found) > 10:
                smells.append({"type": "too_many_globals", "severity": "medium", "detail": f"{len(globals_found)} globals"})

        return smells

    def _detect_duplications(self, code: str) -> List[Dict]:
        """Simple duplicate code detection using line hashing."""
        duplications = []
        lines = code.split("\n")
        # Hash blocks of 5 lines
        block_size = 5
        seen = {}

        for i in range(len(lines) - block_size):
            block = "\n".join(line.strip() for line in lines[i:i + block_size] if line.strip())
            if len(block) < 30:
                continue
            h = hashlib.md5(block.encode()).hexdigest()
            if h in seen:
                duplications.append({
                    "block_hash": h[:8],
                    "lines_a": f"{seen[h]+1}-{seen[h]+block_size}",
                    "lines_b": f"{i+1}-{i+block_size}",
                    "size": block_size,
                })
            else:
                seen[h] = i

        return duplications[:10]  # Cap at 10

    def _find_complexity_hotspots(self, code: str, language: str) -> List[Dict]:
        """Find functions with highest cyclomatic complexity."""
        hotspots = []
        if language != "python":
            return hotspots

        functions = re.finditer(r"^(\s*)def\s+(\w+)\s*\(", code, re.MULTILINE)
        lines = code.split("\n")

        for match in functions:
            func_name = match.group(2)
            start_line = code[:match.start()].count("\n")
            indent = len(match.group(1))

            # Find function end
            end_line = start_line + 1
            for j in range(start_line + 1, len(lines)):
                stripped = lines[j].strip()
                if stripped and not stripped.startswith("#"):
                    current_indent = len(lines[j]) - len(lines[j].lstrip())
                    if current_indent <= indent and stripped:
                        break
                end_line = j

            func_code = "\n".join(lines[start_line:end_line])
            complexity = 1
            for keyword in ["if ", "elif ", "else:", "for ", "while ", "except ", "and ", "or "]:
                complexity += func_code.count(keyword)

            if complexity > 10:
                hotspots.append({
                    "function": func_name,
                    "complexity": complexity,
                    "line": start_line + 1,
                    "severity": "high" if complexity > 20 else "medium",
                })

        return sorted(hotspots, key=lambda x: -x["complexity"])[:5]

    def _ai_refactor(self, code: str, language: str) -> str:
        """Use AI for refactoring suggestions."""
        if not self.openai_client:
            return ""
        try:
            response = self.openai_client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are an expert {language} refactoring advisor. "
                            "Identify the top 3-5 most impactful refactorings. "
                            "Be specific: name patterns, suggest extractions, identify SOLID violations."
                        ),
                    },
                    {"role": "user", "content": f"Suggest refactorings:\n\n{code[:5000]}"},
                ],
                max_tokens=600,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return ""

    def _detect_language(self, path: Path) -> Optional[str]:
        ext_map = {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
            ".go": "go", ".rs": "rust", ".cpp": "cpp", ".c": "cpp",
        }
        return ext_map.get(path.suffix.lower())
