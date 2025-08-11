"""
Image generation service with multiple backend support.
Supports placeholder images, Automa    def _generate_placeholder(self, output_path: Path, label: str = "") -> str:
        """Generate a placeholder image with visible content and label."""
        
        sample_path = Path(settings.assets_dir) / "sample_panel.png"
        
        if sample_path.exists():
            shutil.copy2(sample_path, output_path)
        else:
            # Create a simple colored rectangle if no sample exists
            self._create_simple_placeholder(output_path)
        
        # Overlay border and label so it's clearly not blank
        try:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.open(output_path).convert("RGB")
            dr = ImageDraw.Draw(img)
            w, h = img.size
            
            # Draw border
            dr.rectangle([10, 10, w-10, h-10], outline=(60, 90, 160), width=8)
            # Draw header band
            dr.rectangle([0, 0, w, 80], fill=(60, 90, 160))
            
            # Add text label
            txt = label or "StAnify Placeholder"
            # Try to load a font, fall back to default
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except:
                font = ImageFont.load_default()
                
            dr.text((24, 24), txt[:60], fill=(255, 255, 255), font=font)
            
            img.save(output_path, "PNG")
            logger.info(f"Enhanced placeholder with label '{txt[:30]}...' at {output_path}")
        except Exception as e:
            logger.warning(f"Placeholder overlay failed: {e}")
        
        return str(output_path.resolve()).replace("\\", "/")omfyUI.
"""

import base64
import io
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests
from PIL import Image

from .image_panels_contracts import PanelSpec, SDXLHints
from .settings import settings

logger = logging.getLogger(__name__)


class ImageGenerationError(Exception):
    """Base exception for image generation errors."""
    pass


class ImageService:
    """
    Service for generating images with multiple backend support.
    
    Backends:
    - placeholder: Uses existing local PNG files
    - sdxl-a1111: Automatic1111 REST API with SDXL
    - sdxl-comfyui: ComfyUI graph-based generation (future)
    """
    
    def __init__(self):
        self.backend = settings.image_backend
        self.config = settings.get_image_config()
        
        # Cache for reference images (for img2img)
        self._reference_cache: Dict[str, str] = {}
        
        # Healthcheck for A1111 backend
        if self.backend == "sdxl-a1111":
            self._a1111_healthcheck(self.config["a1111_url"])
    
    def _a1111_healthcheck(self, url: str):
        """Check if A1111 is online and log available models."""
        try:
            r = requests.get(f"{url}/sdapi/v1/sd-models", timeout=10)
            r.raise_for_status()
            models = r.json()
            logger.info(f"A1111 online: {len(models)} models available")
            if models:
                logger.info(f"Available models: {[m.get('title', 'Unknown') for m in models[:3]]}")
        except Exception as e:
            logger.warning(f"A1111 healthcheck failed: {e}")
    
    def generate_panel_image(
        self,
        panel: PanelSpec,
        output_dir: str,
        reference_image_path: Optional[str] = None
    ) -> str:
        """
        Generate an image for a panel using the configured backend.
        
        Args:
            panel: Panel specification with prompts and style
            output_dir: Directory to save generated image
            reference_image_path: Path to reference image (for img2img)
            
        Returns:
            Path to generated image file
            
        Raises:
            ImageGenerationError: If generation fails
        """
        
        output_path = Path(output_dir) / f"panel_{panel.chunk_id}.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.backend == "placeholder":
            return self._generate_placeholder(output_path)
        
        elif self.backend == "sdxl-a1111":
            return self._generate_a1111(panel, output_path, reference_image_path)
        
        elif self.backend == "sdxl-comfyui":
            return self._generate_comfyui(panel, output_path, reference_image_path)
        
        else:
            logger.warning(f"Unknown backend '{self.backend}', falling back to placeholder")
            return self._generate_placeholder(output_path)
    
    def _generate_placeholder(self, output_path: Path) -> str:
        """Generate placeholder image by copying sample asset."""
        
        sample_path = Path(settings.assets_dir) / "sample_panel.png"
        
        if sample_path.exists():
            shutil.copy2(sample_path, output_path)
            logger.info(f"Copied placeholder image to {output_path}")
        else:
            # Create a simple colored rectangle if no sample exists
            self._create_simple_placeholder(output_path)
            logger.info(f"Created simple placeholder at {output_path}")
        
        return str(output_path.resolve()).replace("\\", "/")
    
    def _create_simple_placeholder(self, output_path: Path) -> None:
        """Create a simple colored rectangle as placeholder."""
        
        width = self.config["width"]
        height = self.config["height"]
        
        # Create simple gradient placeholder
        img = Image.new("RGB", (width, height), color=(135, 206, 235))  # Sky blue
        
        # Add some simple graphics (optional)
        try:
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(img)
            
            # Add text
            text = "Generated Image\nPlaceholder"
            draw.text((width//2, height//2), text, fill=(255, 255, 255), anchor="mm")
            
        except ImportError:
            # PIL extras not available, just use solid color
            pass
        
        img.save(output_path, "PNG")
    
    def _generate_a1111(
        self,
        panel: PanelSpec,
        output_path: Path,
        reference_image_path: Optional[str] = None
    ) -> str:
        """Generate image using Automatic1111 API."""
        
        try:
            base_url = self.config["a1111_url"]
            
            # Check if reference image should be used (img2img vs txt2img)
            use_img2img = (
                reference_image_path is not None and 
                panel.reference.use_previous_image
            )
            
            if use_img2img:
                return self._a1111_img2img(panel, output_path, reference_image_path, base_url)
            else:
                return self._a1111_txt2img(panel, output_path, base_url)
                
        except Exception as e:
            logger.error(f"A1111 generation failed: {e}")
            # Fallback to placeholder
            return self._generate_placeholder(output_path)
    
    def _a1111_txt2img(self, panel: PanelSpec, output_path: Path, base_url: str) -> str:
        """Generate image using txt2img API."""
        
        # Build API payload
        payload = {
            "prompt": panel.positive_prompt,
            "negative_prompt": panel.negative_prompt,
            "width": panel.sdxl_hints.width or self.config["width"],
            "height": panel.sdxl_hints.height or self.config["height"],
            "cfg_scale": panel.sdxl_hints.cfg_scale or self.config["cfg_scale"],
            "steps": panel.sdxl_hints.steps or self.config["steps"],
            "sampler_name": panel.sdxl_hints.sampler or self.config["sampler"],
            "batch_size": 1,
            "n_iter": 1,
            "seed": panel.sdxl_hints.seed or -1,
        }
        
        # Add model override (always set from hints or settings)
        model = getattr(panel.sdxl_hints, "model", None) or self.config["a1111_model"]
        if model:
            payload.setdefault("override_settings", {})["sd_model_checkpoint"] = model
        
        logger.info(f"Sending txt2img request to {base_url} with model: {model}")
        
        response = requests.post(
            f"{base_url}/sdapi/v1/txt2img",
            json=payload,
            timeout=settings.http_timeout
        )
        response.raise_for_status()
        
        # Parse response and save image
        result = response.json()
        b64 = result["images"][0]
        
        # Handle data URI wrapper (some A1111 forks include this)
        if "," in b64:  # "data:image/png;base64,<actual_data>"
            b64 = b64.split(",", 1)[1]
        
        image_data = base64.b64decode(b64)
        
        with open(output_path, "wb") as f:
            f.write(image_data)
        
        logger.info(f"Generated txt2img at {output_path}")
        return str(output_path.resolve()).replace("\\", "/")
    
    def _a1111_img2img(
        self,
        panel: PanelSpec,
        output_path: Path,
        reference_image_path: str,
        base_url: str
    ) -> str:
        """Generate image using img2img API with reference."""
        
        # Load and encode reference image
        with open(reference_image_path, "rb") as f:
            ref_image_data = base64.b64encode(f.read()).decode()
        
        # Calculate denoising strength (direct mapping: higher hint = stronger carry-over)
        denoising_strength = min(max(panel.reference.strength_hint or 0.6, 0.1), 0.95)
        
        payload = {
            "init_images": [ref_image_data],
            "prompt": panel.positive_prompt,
            "negative_prompt": panel.negative_prompt,
            "width": panel.sdxl_hints.width or self.config["width"],
            "height": panel.sdxl_hints.height or self.config["height"],
            "cfg_scale": panel.sdxl_hints.cfg_scale or self.config["cfg_scale"],
            "steps": panel.sdxl_hints.steps or self.config["steps"],
            "sampler_name": panel.sdxl_hints.sampler or self.config["sampler"],
            "denoising_strength": denoising_strength,
            "batch_size": 1,
            "n_iter": 1,
            "seed": panel.sdxl_hints.seed or -1,
        }
        
        # Add model override (always set from hints or settings)
        model = getattr(panel.sdxl_hints, "model", None) or self.config["a1111_model"]
        if model:
            payload.setdefault("override_settings", {})["sd_model_checkpoint"] = model
        
        logger.info(f"Sending img2img request to {base_url} with model: {model}, strength: {denoising_strength}")
        
        response = requests.post(
            f"{base_url}/sdapi/v1/img2img",
            json=payload,
            timeout=settings.http_timeout
        )
        response.raise_for_status()
        
        # Parse response and save image
        result = response.json()
        b64 = result["images"][0]
        
        # Handle data URI wrapper (some A1111 forks include this)
        if "," in b64:  # "data:image/png;base64,<actual_data>"
            b64 = b64.split(",", 1)[1]
        
        image_data = base64.b64decode(b64)
        
        with open(output_path, "wb") as f:
            f.write(image_data)
        
        logger.info(f"Generated img2img at {output_path}")
        return str(output_path.resolve()).replace("\\", "/")
    
    def _generate_comfyui(
        self,
        panel: PanelSpec,
        output_path: Path,
        reference_image_path: Optional[str] = None
    ) -> str:
        """Generate image using ComfyUI (future implementation)."""
        
        logger.warning("ComfyUI backend not yet implemented, falling back to placeholder")
        return self._generate_placeholder(output_path)
    
    def generate_panel_batch(
        self,
        panels: list[PanelSpec],
        output_dir: str
    ) -> Dict[str, str]:
        """
        Generate images for multiple panels, handling reference chaining.
        
        Args:
            panels: List of panel specifications
            output_dir: Output directory for images
            
        Returns:
            Dictionary mapping chunk_id to generated image path
        """
        
        results = {}
        previous_image_path = None
        
        for i, panel in enumerate(panels):
            # Determine reference image for this panel
            reference_path = None
            if panel.reference.use_previous_image and previous_image_path:
                reference_path = previous_image_path
            
            # Generate image
            try:
                image_path = self.generate_panel_image(
                    panel=panel,
                    output_dir=output_dir,
                    reference_image_path=reference_path
                )
                
                results[panel.chunk_id] = image_path
                previous_image_path = image_path
                
                logger.info(f"Generated panel {i+1}/{len(panels)}: {panel.chunk_id}")
                
            except Exception as e:
                logger.error(f"Failed to generate panel {panel.chunk_id}: {e}")
                # Continue with placeholder for failed panels
                placeholder_path = self._generate_placeholder(
                    Path(output_dir) / f"panel_{panel.chunk_id}_error.png"
                )
                results[panel.chunk_id] = placeholder_path
        
        return results


# Global service instance
image_service = ImageService()


def generate_panel_image(panel: PanelSpec, output_dir: str, reference_image_path: Optional[str] = None) -> str:
    """
    Convenience function for single panel generation.
    
    Args:
        panel: Panel specification
        output_dir: Output directory
        reference_image_path: Optional reference image path
        
    Returns:
        Path to generated image
    """
    return image_service.generate_panel_image(panel, output_dir, reference_image_path)


def generate_panel_batch(panels: list[PanelSpec], output_dir: str) -> Dict[str, str]:
    """
    Convenience function for batch panel generation.
    
    Args:
        panels: List of panel specifications
        output_dir: Output directory
        
    Returns:
        Dictionary mapping chunk_id to image path
    """
    return image_service.generate_panel_batch(panels, output_dir)
