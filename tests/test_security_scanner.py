"""Tests for codeai_platform.modules.security_scanner module."""

from codeai_platform.config import CodeAIConfig
from codeai_platform.modules.security_scanner import (
    SecurityFinding,
    SecurityScanResult,
    SecurityScanner,
)


def make_config():
    config = CodeAIConfig()
    config.get_openai_client = lambda use_real=False: None
    return config


def make_scanner():
    return SecurityScanner(make_config())


class TestSecurityModels:
    def test_security_finding_to_dict(self):
        finding = SecurityFinding(
            file_path="app.py",
            line=8,
            severity="high",
            category="injection",
            title="eval() usage",
            description="Potential eval usage at line 8",
            cwe="CWE-95",
            suggestion="Avoid eval()",
        )

        payload = finding.to_dict()

        assert payload["file"] == "app.py"
        assert payload["line"] == 8
        assert payload["severity"] == "high"
        assert payload["cwe"] == "CWE-95"

    def test_security_scan_result_to_dict_formats_counts(self):
        result = SecurityScanResult(
            project="demo",
            files_scanned=2,
            findings=[
                SecurityFinding("a.py", 1, "critical", "secrets", "key", "desc"),
                SecurityFinding("b.py", 2, "high", "injection", "eval", "desc"),
            ],
            risk_score=35,
        )

        payload = result.to_dict()

        assert payload["critical"] == 1
        assert payload["high"] == 1
        assert payload["risk_score"] == "35.0"
        assert payload["total_findings"] == 2


class TestSecurityScanner:
    def test_scan_file_detects_secret_injection_crypto_and_path_traversal(self, tmp_path):
        source = tmp_path / "app.py"
        source.write_text(
            "password = 'supersecret'\n"
            "eval(user_input)\n"
            "digest = md5(data)\n"
            "open(base_path + request.args['file'])\n"
        )

        findings = make_scanner().scan_file(str(source))

        categories = {finding.category for finding in findings}
        titles = {finding.title for finding in findings}

        assert "secrets" in categories
        assert "injection" in categories
        assert "crypto" in categories
        assert "path_traversal" in categories
        assert "Hardcoded password" in titles

    def test_scan_file_skips_commented_or_example_secrets(self, tmp_path):
        source = tmp_path / "safe.py"
        source.write_text(
            "# password = 'supersecret'\n"
            "api_key = 'exampleexampleexample'\n"
            "token = 'testtesttesttesttest'\n"
        )

        findings = make_scanner().scan_file(str(source))

        assert findings == []

    def test_scan_project_ignores_vendor_directories(self, tmp_path):
        project = tmp_path / "security_project"
        project.mkdir()
        (project / "main.py").write_text("eval(user_input)\n")
        node_modules = project / "node_modules"
        node_modules.mkdir()
        (node_modules / "ignored.js").write_text("eval(user_input)\n")

        result = make_scanner().scan_project(str(project))

        assert result.files_scanned == 1
        assert len(result.findings) == 1
        assert result.findings[0].title == "eval() usage"
        assert result.risk_score == 10

    def test_calculate_risk_caps_at_100(self):
        findings = [
            SecurityFinding("a.py", 1, "critical", "secrets", "secret", "desc")
            for _ in range(10)
        ]

        assert make_scanner()._calculate_risk(findings) == 100.0
