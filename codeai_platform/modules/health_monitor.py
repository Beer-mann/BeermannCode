"""
Health monitor module for CodeAI Platform.
Monitors Ollama availability, model health, and system resources.
Sends alerts when issues are detected.
"""

import json
import time
import urllib.request
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class ModelHealth:
    """Health status of an individual model."""
    name: str
    available: bool = False
    response_time_ms: float = 0.0
    last_checked: str = ""
    error: str = ""

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "available": self.available,
            "response_time_ms": round(self.response_time_ms, 1),
            "last_checked": self.last_checked,
            "error": self.error,
        }


@dataclass
class SystemHealth:
    """Overall system health."""
    ollama_online: bool = False
    ollama_host: str = ""
    models_available: int = 0
    models_total: int = 0
    model_details: List[ModelHealth] = field(default_factory=list)
    ollama_response_ms: float = 0.0
    timestamp: str = ""
    alerts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "ollama_online": self.ollama_online,
            "ollama_host": self.ollama_host,
            "models": f"{self.models_available}/{self.models_total}",
            "response_ms": round(self.ollama_response_ms, 1),
            "timestamp": self.timestamp,
            "alerts": self.alerts,
            "model_details": [m.to_dict() for m in self.model_details],
        }


HEALTH_LOG = Path("/home/shares/beermann/logs/beermanncode-health.json")


class HealthMonitor:
    """Monitors system and model health."""

    def __init__(self, config):
        self.config = config
        self.last_status: Optional[SystemHealth] = None

    def check_health(self) -> SystemHealth:
        """Full health check: Ollama connectivity + model availability."""
        health = SystemHealth(
            ollama_host=self.config.ollama_host,
            timestamp=datetime.now().isoformat(),
        )

        # Check Ollama connectivity
        start = time.time()
        try:
            url = f"{self.config.ollama_host}/api/tags"
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read())
                health.ollama_online = True
                health.ollama_response_ms = (time.time() - start) * 1000

                available_models = [m["name"] for m in data.get("models", [])]
                health.models_available = len(available_models)
                health.models_total = len(self.config.ollama_models)

                # Check each expected model
                for model_name in self.config.ollama_models:
                    mh = ModelHealth(
                        name=model_name,
                        available=model_name in available_models,
                        last_checked=health.timestamp,
                    )
                    if not mh.available:
                        mh.error = "Model not found on server"
                        health.alerts.append(f"Model missing: {model_name}")
                    health.model_details.append(mh)

        except Exception as e:
            health.ollama_online = False
            health.ollama_response_ms = (time.time() - start) * 1000
            health.alerts.append(f"🚨 Ollama DOWN: {str(e)[:100]}")

        # Check for degraded state
        if health.ollama_online and health.models_available < health.models_total:
            missing = health.models_total - health.models_available
            health.alerts.append(f"⚠️ {missing} models missing from Ollama")

        if health.ollama_online and health.ollama_response_ms > 5000:
            health.alerts.append(f"⚠️ Ollama slow: {health.ollama_response_ms:.0f}ms response")

        self.last_status = health
        self._save_health(health)
        return health

    def test_model(self, model_name: str) -> ModelHealth:
        """Test a specific model by sending a simple prompt."""
        mh = ModelHealth(name=model_name, last_checked=datetime.now().isoformat())

        url = f"{self.config.ollama_host}/api/generate"
        payload = json.dumps({
            "model": model_name,
            "prompt": "Say 'OK' and nothing else.",
            "stream": False,
            "options": {"num_predict": 5},
        }).encode()

        start = time.time()
        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                mh.available = True
                mh.response_time_ms = (time.time() - start) * 1000
        except Exception as e:
            mh.available = False
            mh.response_time_ms = (time.time() - start) * 1000
            mh.error = str(e)[:200]

        return mh

    def test_all_models(self) -> List[ModelHealth]:
        """Test all configured models (slow — sends a prompt to each)."""
        results = []
        for model_name in self.config.ollama_models:
            result = self.test_model(model_name)
            results.append(result)
        return results

    def get_status_summary(self) -> str:
        """Get a human-readable status summary."""
        health = self.check_health()

        if not health.ollama_online:
            return f"🚨 OLLAMA OFFLINE — {health.ollama_host} nicht erreichbar!"

        lines = [
            f"✅ Ollama Online ({health.ollama_response_ms:.0f}ms)",
            f"📦 Modelle: {health.models_available}/{health.models_total}",
        ]

        if health.alerts:
            lines.append("⚠️ Alerts:")
            for alert in health.alerts:
                lines.append(f"  - {alert}")

        return "\n".join(lines)

    def should_alert(self) -> Optional[str]:
        """Check if an alert should be sent. Returns alert message or None."""
        health = self.check_health()

        if not health.ollama_online:
            return (
                f"🚨 *BeermannCode Alert*\n\n"
                f"Ollama ist OFFLINE!\n"
                f"Host: {health.ollama_host}\n"
                f"Zeit: {health.timestamp}\n\n"
                f"Autonomes Coding pausiert bis Ollama wieder erreichbar ist."
            )

        if health.alerts:
            alert_text = "\n".join(f"- {a}" for a in health.alerts)
            return (
                f"⚠️ *BeermannCode Warning*\n\n"
                f"{alert_text}\n"
                f"Zeit: {health.timestamp}"
            )

        return None

    def _save_health(self, health: SystemHealth):
        """Save health check to log file."""
        HEALTH_LOG.parent.mkdir(parents=True, exist_ok=True)

        # Append to log (keep last 100 entries)
        history = []
        if HEALTH_LOG.exists():
            try:
                history = json.loads(HEALTH_LOG.read_text())
            except Exception:
                history = []

        history.append(health.to_dict())
        history = history[-100:]  # Keep last 100

        with open(HEALTH_LOG, "w") as f:
            json.dump(history, f, indent=2)
