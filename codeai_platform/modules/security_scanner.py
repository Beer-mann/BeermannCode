"""
Security scanner module for CodeAI Platform.
Detects common security vulnerabilities in source code.
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SecurityFinding:
    """A security vulnerability finding."""
    file_path: str
    line: int
    severity: str  # critical, high, medium, low, info
    category: str  # injection, secrets, crypto, auth, xss, path_traversal
    title: str
    description: str
    cwe: str = ""  # CWE reference
    suggestion: str = ""

    def to_dict(self) -> Dict:
        return {
            "file": self.file_path,
            "line": self.line,
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "cwe": self.cwe,
            "suggestion": self.suggestion,
        }


@dataclass
class SecurityScanResult:
    """Result of a security scan."""
    project: str
    files_scanned: int = 0
    findings: List[SecurityFinding] = None
    risk_score: float = 0.0  # 0-100
    ai_assessment: str = ""

    def __post_init__(self):
        if self.findings is None:
            self.findings = []

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "high")

    def to_dict(self) -> Dict:
        return {
            "project": self.project,
            "files_scanned": self.files_scanned,
            "total_findings": len(self.findings),
            "critical": self.critical_count,
            "high": self.high_count,
            "risk_score": f"{self.risk_score:.1f}",
            "findings": [f.to_dict() for f in self.findings],
            "ai_assessment": self.ai_assessment,
        }


# Patterns to detect
SECRET_PATTERNS = [
    (r"(?i)(api[_-]?key|apikey)\s*[=:]\s*['\"]([a-zA-Z0-9_\-]{16,})['\"]", "Hardcoded API key", "CWE-798"),
    (r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"](.{4,})['\"]", "Hardcoded password", "CWE-798"),
    (r"(?i)(secret|token)\s*[=:]\s*['\"]([a-zA-Z0-9_\-]{16,})['\"]", "Hardcoded secret/token", "CWE-798"),
    (r"(?i)(aws_access_key_id|aws_secret)\s*[=:]\s*['\"]([A-Z0-9]{16,})['\"]", "AWS credentials", "CWE-798"),
    (r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", "Embedded private key", "CWE-321"),
    (r"(?i)Bearer\s+[a-zA-Z0-9_\-.]{20,}", "Hardcoded Bearer token", "CWE-798"),
]

INJECTION_PATTERNS = {
    "python": [
        (r"os\.system\s*\(", "OS command execution", "CWE-78", "Use subprocess with shell=False"),
        (r"subprocess\.\w+\(.*shell\s*=\s*True", "Shell injection risk", "CWE-78", "Set shell=False"),
        (r"eval\s*\(", "eval() usage", "CWE-95", "Avoid eval(); use ast.literal_eval() for data"),
        (r"exec\s*\(", "exec() usage", "CWE-95", "Avoid exec(); find safer alternatives"),
        (r"__import__\s*\(", "Dynamic import", "CWE-95", "Use static imports"),
        (r"pickle\.loads?\s*\(", "Unsafe deserialization", "CWE-502", "Use json or a safe serializer"),
        (r"yaml\.load\s*\((?!.*Loader)", "Unsafe YAML loading", "CWE-502", "Use yaml.safe_load()"),
        (r"\.format\(.*\)\s*$.*execute\(", "SQL injection via format", "CWE-89", "Use parameterized queries"),
        (r"f['\"].*\{.*\}.*['\"].*execute\(", "SQL injection via f-string", "CWE-89", "Use parameterized queries"),
    ],
    "javascript": [
        (r"eval\s*\(", "eval() usage", "CWE-95", "Avoid eval()"),
        (r"innerHTML\s*=", "XSS via innerHTML", "CWE-79", "Use textContent or sanitize input"),
        (r"document\.write\s*\(", "XSS via document.write", "CWE-79", "Use DOM manipulation instead"),
        (r"new\s+Function\s*\(", "Dynamic code execution", "CWE-95", "Avoid new Function()"),
        (r"child_process\.exec\s*\(", "Command injection", "CWE-78", "Use execFile with args array"),
    ],
}

CRYPTO_PATTERNS = [
    (r"(?i)md5\s*\(", "Weak hash (MD5)", "CWE-328", "Use SHA-256 or bcrypt"),
    (r"(?i)sha1\s*\(", "Weak hash (SHA-1)", "CWE-328", "Use SHA-256 or better"),
    (r"(?i)DES\b", "Weak encryption (DES)", "CWE-327", "Use AES-256"),
    (r"(?i)random\(\)", "Insecure random", "CWE-338", "Use secrets module for crypto"),
]


class SecurityScanner:
    """Scans code for security vulnerabilities."""

    def __init__(self, config):
        self.config = config
        self.openai_client = config.get_openai_client()

    def scan_file(self, file_path: str) -> List[SecurityFinding]:
        """Scan a single file for security issues."""
        path = Path(file_path)
        if not path.exists():
            return []

        try:
            code = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        language = self._detect_language(path)
        findings = []
        lines = code.split("\n")

        # Secret detection (all languages)
        for i, line in enumerate(lines, 1):
            for pattern, title, cwe in SECRET_PATTERNS:
                if re.search(pattern, line):
                    # Skip if it's a comment or test/example
                    stripped = line.strip()
                    if stripped.startswith(("#", "//", "*", "/*")):
                        continue
                    if "example" in line.lower() or "test" in line.lower() or "xxx" in line.lower():
                        continue
                    findings.append(SecurityFinding(
                        file_path=file_path,
                        line=i,
                        severity="critical",
                        category="secrets",
                        title=title,
                        description=f"Potential secret found at line {i}",
                        cwe=cwe,
                        suggestion="Move to environment variable or secret manager",
                    ))

        # Language-specific injection patterns
        if language and language in INJECTION_PATTERNS:
            for pattern, title, cwe, suggestion in INJECTION_PATTERNS[language]:
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line):
                        stripped = line.strip()
                        if stripped.startswith(("#", "//", "*")):
                            continue
                        findings.append(SecurityFinding(
                            file_path=file_path,
                            line=i,
                            severity="high",
                            category="injection",
                            title=title,
                            description=f"Potential {title} at line {i}",
                            cwe=cwe,
                            suggestion=suggestion,
                        ))

        # Crypto patterns
        for pattern, title, cwe, suggestion in CRYPTO_PATTERNS:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    findings.append(SecurityFinding(
                        file_path=file_path,
                        line=i,
                        severity="medium",
                        category="crypto",
                        title=title,
                        description=f"{title} detected at line {i}",
                        cwe=cwe,
                        suggestion=suggestion,
                    ))

        # Path traversal
        for i, line in enumerate(lines, 1):
            if re.search(r"open\s*\(.*\+|os\.path\.join\(.*request|Path\(.*request", line):
                findings.append(SecurityFinding(
                    file_path=file_path,
                    line=i,
                    severity="high",
                    category="path_traversal",
                    title="Potential path traversal",
                    description="User input may be used in file path",
                    cwe="CWE-22",
                    suggestion="Validate and sanitize file paths",
                ))

        return findings

    def scan_project(self, project_path: str) -> SecurityScanResult:
        """Scan entire project for security issues."""
        project = Path(project_path)
        result = SecurityScanResult(project=project.name)
        ignore = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
        exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".sh", ".env", ".yaml", ".yml", ".json"}

        for file_path in project.rglob("*"):
            if not file_path.is_file():
                continue
            if any(p in ignore for p in file_path.parts):
                continue
            if file_path.suffix not in exts and file_path.name not in {".env", "Dockerfile"}:
                continue

            result.files_scanned += 1
            findings = self.scan_file(str(file_path))
            result.findings.extend(findings)

        # Calculate risk score
        result.risk_score = self._calculate_risk(result.findings)

        # AI assessment for critical findings
        if result.critical_count > 0 and self.openai_client:
            result.ai_assessment = self._ai_assess(result)

        return result

    def _calculate_risk(self, findings: List[SecurityFinding]) -> float:
        """Calculate risk score 0-100."""
        if not findings:
            return 0.0
        weights = {"critical": 25, "high": 10, "medium": 3, "low": 1, "info": 0.5}
        score = sum(weights.get(f.severity, 1) for f in findings)
        return min(100.0, score)

    def _ai_assess(self, result: SecurityScanResult) -> str:
        """Use AI to provide security assessment."""
        if not self.openai_client:
            return ""
        try:
            critical_findings = [f.to_dict() for f in result.findings if f.severity in ("critical", "high")][:10]
            response = self.openai_client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a security engineer. Assess these findings and provide actionable remediation steps. Be concise.",
                    },
                    {
                        "role": "user",
                        "content": f"Security findings for {result.project}:\n{json.dumps(critical_findings, indent=2)}",
                    },
                ],
                max_tokens=500,
                temperature=0.2,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return ""

    def _detect_language(self, path: Path) -> Optional[str]:
        ext_map = {
            ".py": "python", ".js": "javascript", ".ts": "javascript",
            ".jsx": "javascript", ".tsx": "javascript", ".java": "java",
            ".go": "go", ".rs": "rust",
        }
        return ext_map.get(path.suffix.lower())


# Need json import for AI assessment
import json
