"""Tests for codeai_platform.config module."""

import pytest
from codeai_platform.config import CodeAIConfig


def make_config(**kwargs):
    """Create a CodeAIConfig with get_openai_client mocked to return None."""
    config = CodeAIConfig(**kwargs)
    config.get_openai_client = lambda use_real=False: None
    return config


class TestCodeAIConfigDefaults:
    def test_default_project_name(self):
        config = CodeAIConfig()
        assert config.project_name == "default_project"

    def test_default_supported_languages(self):
        config = CodeAIConfig()
        assert "python" in config.supported_languages
        assert "javascript" in config.supported_languages

    def test_default_max_tokens_positive(self):
        config = CodeAIConfig()
        assert config.max_tokens > 0

    def test_default_temperature_in_range(self):
        config = CodeAIConfig()
        assert 0 <= config.temperature <= 2

    def test_feature_flags_enabled_by_default(self):
        config = CodeAIConfig()
        assert config.enable_code_analysis
        assert config.enable_code_generation
        assert config.enable_code_review
        assert config.enable_security_scan


class TestCodeAIConfigFromDict:
    def test_from_dict_basic(self):
        config = CodeAIConfig.from_dict({"project_name": "myproject", "max_tokens": 1024})
        assert config.project_name == "myproject"
        assert config.max_tokens == 1024

    def test_from_dict_ignores_unknown_keys(self):
        config = CodeAIConfig.from_dict({"unknown_key": "value", "project_name": "test"})
        assert config.project_name == "test"
        assert not hasattr(config, "unknown_key")

    def test_from_dict_defaults_for_missing_keys(self):
        config = CodeAIConfig.from_dict({})
        assert config.project_name == "default_project"


class TestCodeAIConfigValidate:
    def test_valid_config_passes(self):
        config = make_config()
        assert config.validate() is True

    def test_empty_project_name_raises(self):
        config = make_config(project_name="")
        with pytest.raises(ValueError, match="Project name"):
            config.validate()

    def test_zero_max_tokens_raises(self):
        config = make_config(max_tokens=0)
        with pytest.raises(ValueError, match="max_tokens"):
            config.validate()

    def test_negative_max_tokens_raises(self):
        config = make_config(max_tokens=-1)
        with pytest.raises(ValueError, match="max_tokens"):
            config.validate()

    def test_invalid_temperature_raises(self):
        config = make_config(temperature=3.0)
        with pytest.raises(ValueError, match="temperature"):
            config.validate()

    def test_invalid_review_depth_raises(self):
        config = make_config(review_depth="extreme")
        with pytest.raises(ValueError, match="review_depth"):
            config.validate()

    def test_valid_review_depths(self):
        for depth in ["basic", "standard", "comprehensive"]:
            config = make_config(review_depth=depth)
            assert config.validate() is True

    def test_invalid_generation_style_raises(self):
        config = make_config(generation_style="fancy")
        with pytest.raises(ValueError, match="generation_style"):
            config.validate()

    def test_valid_generation_styles(self):
        for style in ["minimal", "clean", "verbose"]:
            config = make_config(generation_style=style)
            assert config.validate() is True


class TestCodeAIConfigGetModelForTask:
    def test_returns_string(self):
        config = make_config()
        result = config.get_model_for_task("code_generation")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_known_task_returns_routed_model(self):
        config = make_config()
        model = config.get_model_for_task("code_generation")
        assert model in config.model_routing["code_generation"]

    def test_unknown_task_returns_fallback(self):
        config = make_config()
        model = config.get_model_for_task("nonexistent_task_xyz")
        assert isinstance(model, str)


class TestCodeAIConfigGetExternalModel:
    def test_returns_none_when_external_disabled(self):
        config = make_config(enable_external=False)
        result = config.get_external_model("code_generation", tier=2)
        assert result is None

    def test_returns_none_when_tier_exceeded(self):
        config = make_config(enable_external=True, max_tier=1)
        result = config.get_external_model("code_generation", tier=2)
        assert result is None

    def test_returns_model_when_external_enabled(self):
        config = make_config(enable_external=True, max_tier=4)
        result = config.get_external_model("code_generation", tier=2)
        assert result is not None
        assert "name" in result


class TestCodeAIConfigToDict:
    def test_to_dict_contains_expected_keys(self):
        config = make_config()
        d = config.to_dict()
        assert "project_name" in d
        assert "supported_languages" in d
        assert "max_tokens" in d
        assert "enable_code_analysis" in d

    def test_to_dict_project_name(self):
        config = make_config(project_name="testproject")
        assert config.to_dict()["project_name"] == "testproject"
