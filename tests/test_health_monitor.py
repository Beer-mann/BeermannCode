"""Tests for codeai_platform.modules.health_monitor module."""

import json
from urllib.error import URLError

from codeai_platform.config import CodeAIConfig
from codeai_platform.modules import health_monitor as health_module
from codeai_platform.modules.health_monitor import HealthMonitor, ModelHealth, SystemHealth


def make_config():
    config = CodeAIConfig(
        ollama_host="http://ollama.local:11434",
        ollama_models={"model-a": {}, "model-b": {}},
    )
    config.get_openai_client = lambda use_real=False: None
    return config


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestHealthModels:
    def test_model_health_to_dict_rounds_response_time(self):
        model = ModelHealth(name="qwen", available=True, response_time_ms=12.34)

        assert model.to_dict()["response_time_ms"] == 12.3

    def test_system_health_to_dict_contains_model_summary(self):
        system = SystemHealth(
            ollama_online=True,
            ollama_host="http://ollama",
            models_available=1,
            models_total=2,
            model_details=[ModelHealth(name="qwen", available=True)],
        )

        payload = system.to_dict()

        assert payload["models"] == "1/2"
        assert payload["model_details"][0]["name"] == "qwen"


class TestHealthMonitor:
    def test_check_health_marks_missing_models_and_saves_status(self, monkeypatch):
        monitor = HealthMonitor(make_config())
        saved = []

        monkeypatch.setattr(
            health_module.urllib.request,
            "urlopen",
            lambda *args, **kwargs: FakeResponse({"models": [{"name": "model-a"}]}),
        )
        monkeypatch.setattr(monitor, "_save_health", lambda health: saved.append(health))

        health = monitor.check_health()

        assert health.ollama_online is True
        assert health.models_available == 1
        assert health.models_total == 2
        assert any(detail.name == "model-b" and not detail.available for detail in health.model_details)
        assert any("Model missing: model-b" in alert for alert in health.alerts)
        assert saved == [health]

    def test_check_health_handles_ollama_outage(self, monkeypatch):
        monitor = HealthMonitor(make_config())

        def raise_url_error(*args, **kwargs):
            raise URLError("down")

        monkeypatch.setattr(health_module.urllib.request, "urlopen", raise_url_error)
        monkeypatch.setattr(monitor, "_save_health", lambda health: None)

        health = monitor.check_health()

        assert health.ollama_online is False
        assert any("Ollama DOWN" in alert for alert in health.alerts)

    def test_test_model_returns_error_when_request_fails(self, monkeypatch):
        monitor = HealthMonitor(make_config())

        def raise_url_error(*args, **kwargs):
            raise URLError("broken")

        monkeypatch.setattr(health_module.urllib.request, "urlopen", raise_url_error)

        result = monitor.test_model("model-a")

        assert result.available is False
        assert "broken" in result.error

    def test_should_alert_returns_warning_text_when_alerts_exist(self, monkeypatch):
        monitor = HealthMonitor(make_config())
        health = SystemHealth(
            ollama_online=True,
            ollama_host="http://ollama.local:11434",
            timestamp="2025-01-01T00:00:00",
            alerts=["Model missing: model-b"],
        )

        monkeypatch.setattr(monitor, "check_health", lambda: health)

        alert = monitor.should_alert()

        assert "BeermannCode Warning" in alert
        assert "Model missing: model-b" in alert

    def test_save_health_keeps_last_100_entries(self, tmp_path, monkeypatch):
        log_path = tmp_path / "health.json"
        monitor = HealthMonitor(make_config())
        history = [{"timestamp": str(i)} for i in range(100)]
        log_path.write_text(json.dumps(history))
        monkeypatch.setattr(health_module, "HEALTH_LOG", log_path)

        monitor._save_health(SystemHealth(timestamp="newest"))

        saved = json.loads(log_path.read_text())
        assert len(saved) == 100
        assert saved[0]["timestamp"] == "1"
        assert saved[-1]["timestamp"] == "newest"
