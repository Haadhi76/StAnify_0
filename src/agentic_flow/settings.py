"""
Application settings and configuration.
Handles backend selection for image generation and other configurable options.
"""

import os
from typing import Literal, Optional

# Image generation backend options
ImageBackend = Literal["placeholder", "sdxl-a1111", "sdxl-comfyui"]


class Settings:
    """Application configuration settings."""
    
    def __init__(self):
        # Image generation backend
        self.image_backend: ImageBackend = os.getenv("IMAGE_BACKEND", "placeholder")
        
        # Automatic1111 settings
        self.a1111_base_url: str = os.getenv("A1111_BASE_URL", "http://127.0.0.1:7860")
        self.a1111_model: str = os.getenv("A1111_MODEL", "sdxl_base_1.0")
        
        # ComfyUI settings
        self.comfyui_base_url: str = os.getenv("COMFYUI_BASE_URL", "http://127.0.0.1:8188")
        self.comfyui_workflow_path: Optional[str] = os.getenv("COMFYUI_WORKFLOW_PATH")
        
        # Default SDXL parameters
        self.default_width: int = int(os.getenv("SDXL_WIDTH", "1024"))
        self.default_height: int = int(os.getenv("SDXL_HEIGHT", "768"))
        self.default_cfg_scale: float = float(os.getenv("SDXL_CFG_SCALE", "6.5"))
        self.default_steps: int = int(os.getenv("SDXL_STEPS", "30"))
        self.default_sampler: str = os.getenv("SDXL_SAMPLER", "DPM++ 2M Karras")
        
        # Paths
        self.output_dir: str = os.getenv("OUTPUT_DIR", "./exports")
        self.assets_dir: str = os.getenv("ASSETS_DIR", "./assets")
        
        # LLM settings
        self.llm_model: str = os.getenv("LLM_MODEL", "gpt-4")
        self.llm_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
        
        # Timeouts and retries
        self.http_timeout: float = float(os.getenv("HTTP_TIMEOUT", "60.0"))
        self.max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
        
        # Debug and logging
        self.debug_mode: bool = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    def validate(self) -> bool:
        """
        Validate current settings and return True if valid.
        
        Returns:
            True if settings are valid, False otherwise
        """
        # Validate image backend
        if self.image_backend not in ["placeholder", "sdxl-a1111", "sdxl-comfyui"]:
            print(f"Warning: Invalid image_backend '{self.image_backend}', falling back to 'placeholder'")
            self.image_backend = "placeholder"
        
        # Validate dimensions
        if self.default_width <= 0 or self.default_height <= 0:
            print(f"Warning: Invalid dimensions {self.default_width}x{self.default_height}, using defaults")
            self.default_width = 1024
            self.default_height = 768
        
        # Check API keys if using real LLM backends
        if self.llm_model.startswith("gpt-") and not self.llm_api_key:
            print("Warning: OpenAI API key not found for GPT model")
        
        if self.llm_model.startswith("claude-") and not self.anthropic_api_key:
            print("Warning: Anthropic API key not found for Claude model")
        
        return True
    
    def get_image_config(self) -> dict:
        """Get image generation configuration."""
        return {
            "backend": self.image_backend,
            "width": self.default_width,
            "height": self.default_height,
            "cfg_scale": self.default_cfg_scale,
            "steps": self.default_steps,
            "sampler": self.default_sampler,
            "a1111_url": self.a1111_base_url,
            "a1111_model": self.a1111_model,
            "comfyui_url": self.comfyui_base_url,
            "comfyui_workflow": self.comfyui_workflow_path,
        }
    
    def get_llm_config(self) -> dict:
        """Get LLM configuration."""
        return {
            "model": self.llm_model,
            "openai_api_key": self.llm_api_key,
            "anthropic_api_key": self.anthropic_api_key,
            "timeout": self.http_timeout,
            "max_retries": self.max_retries,
        }


# Global settings instance
settings = Settings()

# Validate on import
settings.validate()
