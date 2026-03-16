"""Tests for CodeAIConfig."""

import pytest
from codeai_platform import CodeAIConfig


class TestConfig:
    def test_defaults(self):
        config = CodeAIConfig()
        assert config.project_name == "default_project"
        assert "python" in config.supported_languages
        assert config.max_tokens == 2048
        assert config.openai_model == "gpt-4o-mini"

    def test_validate_passes_for_valid_config(self):
        config = CodeAIConfig()
        assert config.validate() is True

    def test_validate_raises_on_empty_project_name(self):
        config = CodeAIConfig(project_name="")
        with pytest.raises(ValueError, match="Project name"):
            config.validate()

    def test_validate_raises_on_bad_max_tokens(self):
        config = CodeAIConfig(max_tokens=0)
        with pytest.raises(ValueError, match="max_tokens"):
            config.validate()

    def test_validate_raises_on_bad_temperature(self):
        config = CodeAIConfig(temperature=3.0)
        with pytest.raises(ValueError, match="temperature"):
            config.validate()

    def test_validate_raises_on_bad_review_depth(self):
        config = CodeAIConfig(review_depth="ultra")
        with pytest.raises(ValueError, match="review_depth"):
            config.validate()

    def test_get_openai_client_returns_none_without_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        config = CodeAIConfig()
        assert config.get_openai_client() is None

    def test_to_dict_round_trip(self):
        config = CodeAIConfig(project_name="test_proj")
        d = config.to_dict()
        assert d["project_name"] == "test_proj"
        assert "supported_languages" in d

    def test_from_dict(self):
        config = CodeAIConfig.from_dict({"project_name": "hello"})
        assert config.project_name == "hello"
