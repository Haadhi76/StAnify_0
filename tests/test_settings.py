"""
Tests for settings and configuration.
"""

import os
from unittest.mock import patch

from src.agentic_flow.settings import Settings


class TestSettings:
    """Test settings functionality."""
    
    def test_settings_defaults(self):
        """Test default settings values."""
        settings = Settings()
        
        assert settings.image_backend == "placeholder"
        assert settings.a1111_base_url == "http://127.0.0.1:7860"
        assert settings.default_width == 1024
        assert settings.default_height == 768
        assert settings.llm_model == "gpt-4"
        assert settings.max_retries == 3
    
    def test_settings_from_environment(self):
        """Test settings loading from environment variables."""
        env_vars = {
            "IMAGE_BACKEND": "sdxl-a1111",
            "A1111_BASE_URL": "http://custom:8080",
            "SDXL_WIDTH": "512",
            "SDXL_HEIGHT": "512",
            "LLM_MODEL": "gpt-3.5-turbo",
            "MAX_RETRIES": "5",
            "DEBUG": "true"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.image_backend == "sdxl-a1111"
            assert settings.a1111_base_url == "http://custom:8080"
            assert settings.default_width == 512
            assert settings.default_height == 512
            assert settings.llm_model == "gpt-3.5-turbo"
            assert settings.max_retries == 5
            assert settings.debug_mode is True
    
    def test_settings_validation(self):
        """Test settings validation."""
        settings = Settings()
        
        # Test invalid backend
        settings.image_backend = "invalid_backend"
        result = settings.validate()
        
        assert result is True  # Should still return True but fix the value
        assert settings.image_backend == "placeholder"  # Should be corrected
    
    def test_settings_invalid_dimensions(self):
        """Test handling of invalid dimensions."""
        with patch.dict(os.environ, {"SDXL_WIDTH": "-100", "SDXL_HEIGHT": "0"}):
            settings = Settings()
            settings.validate()
            
            # Should be corrected to defaults
            assert settings.default_width == 1024
            assert settings.default_height == 768
    
    def test_get_image_config(self):
        """Test image configuration retrieval."""
        settings = Settings()
        config = settings.get_image_config()
        
        required_keys = [
            "backend", "width", "height", "cfg_scale", "steps", 
            "sampler", "a1111_url", "a1111_model", "comfyui_url"
        ]
        
        for key in required_keys:
            assert key in config
        
        assert config["backend"] == settings.image_backend
        assert config["width"] == settings.default_width
    
    def test_get_llm_config(self):
        """Test LLM configuration retrieval."""
        settings = Settings()
        config = settings.get_llm_config()
        
        required_keys = [
            "model", "openai_api_key", "anthropic_api_key", 
            "timeout", "max_retries"
        ]
        
        for key in required_keys:
            assert key in config
        
        assert config["model"] == settings.llm_model
        assert config["max_retries"] == settings.max_retries
    
    def test_api_key_warnings(self):
        """Test API key validation warnings."""
        # Test with GPT model but no OpenAI key
        with patch.dict(os.environ, {"LLM_MODEL": "gpt-4"}, clear=True):
            settings = Settings()
            # Should validate without error but may log warning
            result = settings.validate()
            assert result is True
    
    def test_boolean_parsing(self):
        """Test boolean environment variable parsing."""
        # Test various boolean representations
        test_cases = [
            ("true", True),
            ("True", True),
            ("false", False),
            ("False", False),
            ("yes", False),  # Only "true" should be True
            ("", False)
        ]
        
        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"DEBUG": env_value}):
                settings = Settings()
                assert settings.debug_mode == expected
