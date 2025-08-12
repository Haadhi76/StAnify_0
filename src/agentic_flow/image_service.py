"""
Image generation service with multiple backend support.
Supports placeholder images, Automatic1111, and ComfyUI.
"""

import base64
import io
import json
import logging
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests
from PIL import Image

from .image_panels_contracts import PanelSpec, SDXLHints
from .settings import settings

logger = logging.getLogger(__name__)

# Circuit breaker constants
HEALTH_TTL_SEC = 30         # cache health result for 30s
CB_OPEN_SEC    = 60         # circuit open for 60s after persistent failures
MAX_FAILS      = 2          # open the circuit after N consecutive failures

# SDXL 1.0 allowed dimensions for Stability engines API
_SDXL10_ALLOWED = [
    (1024,1024),(1152,896),(896,1152),
    (1216,832),(832,1216),(1344,768),
    (768,1344),(1536,640),(640,1536),
]

def _snap_to_sdxl10_allowed(w: int, h: int) -> tuple[int,int]:
    """Snap dimensions to SDXL 1.0 allowed sizes for Stability engines API."""
    target_area = w*h
    target_ar = w/h
    best = None
    best_score = 10**9
    for aw, ah in _SDXL10_ALLOWED:
        area = aw*ah
        ar = aw/ah
        score = abs(area - target_area) + 2000*abs(ar - target_ar)
        if score < best_score:
            best_score = score; best = (aw, ah)
    return best

def _is_placeholder_or_disallowed(path: str) -> bool:
    """Check if image is a placeholder or has disallowed dimensions for SDXL engines."""
    try:
        im = Image.open(path)
        w, h = im.size
        return (w, h) not in _SDXL10_ALLOWED
    except Exception:
        return True


@dataclass
class HealthState:
    """Tracks health status and circuit breaker state for A1111."""
    a1111_ok: bool = False
    last_check_ts: float = 0.0
    consecutive_failures: int = 0
    cb_open_until: float = 0.0


class ImageGenerationError(Exception):
    """Base exception for image generation errors."""
    pass


class ImageService:
    """
    Service for generating images with multiple backend support.
    
    Backends:
    - auto: Automatically choose best available backend
    - placeholder: Uses existing local PNG files
    - sdxl-a1111: Automatic1111 REST API with SDXL
    - sdxl-comfyui: ComfyUI graph-based generation (future)
    """
    
    def __init__(self):
        self.backend = settings.image_backend        # "auto" or explicit
        self.config = settings.get_image_config()
        self._health = HealthState()
        
        # Cache for reference images (for img2img)
        self._reference_cache: Dict[str, str] = {}
        
        # Choose initial active backend
        self._active_backend = self._choose_backend(initial=True)
    
    def _a1111_available(self) -> bool:
        """Check if A1111 is available with circuit breaker logic."""
        # Skip A1111 checks entirely when using stability backend
        if self._active_backend == "stability":
            return False
            
        now = time.time()
        
        # Circuit breaker open?
        if now < self._health.cb_open_until:
            logger.debug("A1111 circuit breaker open")
            return False
            
        # Cached recent check?
        if (now - self._health.last_check_ts) < HEALTH_TTL_SEC:
            return self._health.a1111_ok
            
        # Fresh check
        try:
            r = requests.get(f"{self.config['a1111_url']}/sdapi/v1/sd-models", timeout=5)
            r.raise_for_status()
            self._health.a1111_ok = True
            self._health.consecutive_failures = 0
            logger.debug("A1111 health check: OK")
        except Exception as e:
            self._health.a1111_ok = False
            self._health.consecutive_failures += 1
            logger.debug(f"A1111 health check failed: {e}")
            
            # Open circuit breaker after persistent failures
            if self._health.consecutive_failures >= MAX_FAILS:
                self._health.cb_open_until = now + CB_OPEN_SEC
                logger.warning(f"A1111 circuit breaker opened after {MAX_FAILS} failures")
        finally:
            self._health.last_check_ts = now
            
        return self._health.a1111_ok
    
    def _choose_backend(self, initial=False) -> str:
        """Choose the best available backend based on configuration and health."""
        configured = self.backend  # "auto", "stability", "sdxl-a1111", "placeholder"
        
        if configured == "auto":
            # Priority order: Stability (if API key) > A1111 (if available) > placeholder
            if settings.stability_api_key:
                chosen = "stability"
                if initial:
                    logger.info(f"Auto backend selection: {chosen}")
                return chosen
            elif self._a1111_available():
                chosen = "sdxl-a1111"
            else:
                chosen = "placeholder"
                
            if initial:
                logger.info(f"Auto backend selection: {chosen}")
            return chosen
            
        # Explicit config: honor it, but we'll still failover per-call
        return configured
    
    def get_status(self) -> dict:
        """Get current backend status for monitoring and UI."""
        # Only check A1111 if actually using it
        a1111_ok = self._a1111_available() if self._active_backend in ["sdxl-a1111", "auto"] else False
        
        return {
            "configured": self.backend,
            "active": self._active_backend,
            "a1111_ok": a1111_ok,
            "cb_open_until": self._health.cb_open_until,
            "last_check": self._health.last_check_ts,
            "consecutive_failures": self._health.consecutive_failures,
        }
    
    def _ensure_active(self):
        """Re-evaluate active backend in auto mode."""
        if self.backend == "auto":
            new_backend = self._choose_backend()
            if new_backend != self._active_backend:
                logger.info(f"Image backend switched: {self._active_backend} → {new_backend}")
                self._active_backend = new_backend
    
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
        # Re-evaluate active backend in auto mode
        self._ensure_active()
        backend = self._active_backend
        
        output_path = Path(output_dir) / f"panel_{panel.chunk_id}.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if backend == "placeholder":
            return self._generate_placeholder(output_path, label=panel.caption or "placeholder")
        
        elif backend == "sdxl-a1111":
            try:
                return self._generate_a1111(panel, output_path, reference_image_path)
            except Exception as e:
                # Mark health failure & maybe open circuit - only when actually using A1111
                if self.config["backend"] in ["sdxl-a1111", "auto"]:
                    self._health.a1111_ok = False
                    self._health.consecutive_failures += 1
                    if self._health.consecutive_failures >= MAX_FAILS:
                        self._health.cb_open_until = time.time() + CB_OPEN_SEC
                        logger.warning(f"A1111 circuit breaker opened due to: {e}")
                    logger.error(f"A1111 generation failed: {e}")
                # Explicit mode: still fall back; auto mode: will switch next call
                return self._generate_placeholder(output_path, label="A1111 offline")
        
        elif backend == "sdxl-comfyui":
            return self._generate_comfyui(panel, output_path, reference_image_path)
        
        elif backend == "stability":
            try:
                return self._generate_stability(panel, output_path, reference_image_path)
            except Exception as e:
                logger.error(f"Stability generation failed: {e}")
                return self._generate_placeholder(output_path, label=f"Panel {panel.chunk_id}")
        
        else:
            logger.warning(f"Unknown backend '{backend}', falling back to placeholder")
            return self._generate_placeholder(output_path, label=f"Panel {panel.chunk_id}")
    
    def _generate_placeholder(self, output_path: Path, label: str = "") -> str:
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
                
        except requests.HTTPError as e:
            logger.error(f"A1111 HTTP error: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"A1111 response: {e.response.text}")
            # Fallback to placeholder
            return self._generate_placeholder(output_path, label=f"A1111 Error: {panel.chunk_id}")
        except Exception as e:
            logger.error(f"A1111 generation failed: {e}")
            # Fallback to placeholder
            return self._generate_placeholder(output_path, label=f"Failed: {panel.chunk_id}")
    
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
    
    def _stability_headers(self) -> dict:
        """Get headers for Stability AI API requests."""
        key = settings.stability_api_key
        if not key:
            raise ImageGenerationError("STABILITY_API_KEY missing")
        return {
            "Authorization": f"Bearer {key}",
            "User-Agent": "StAnify/1.0 Educational-Content-Generator",
            "Accept": "application/json"
        }
    
    def _get_stability_balance(self) -> float:
        """Get current account balance from Stability API."""
        try:
            base_url = self.config["stability_url"]
            headers = self._stability_headers()
            response = requests.get(f"{base_url}/v1/user/balance", headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return float(data.get("credits", 0))
        except Exception as e:
            logger.warning(f"Failed to get Stability balance: {e}")
            return None
    def _stability_extract_b64(self, data: dict) -> bytes:
        """
        Extract base64 image data from Stability API response.
        Handles both engines and images API response formats.
        """
        b64 = None
        if isinstance(data, dict):
            # Images API variants
            b64 = data.get("image") or (data.get("images")[0] if isinstance(data.get("images"), list) and data["images"] else None)
            # Artifacts shape (engines API)
            if not b64 and "artifacts" in data:
                for a in data["artifacts"]:
                    if a.get("finishReason") not in {"CONTENT_FILTERED", "filtered"}:
                        b64 = a.get("base64") or a.get("image")
                        if b64: 
                            break
        
        if not b64:
            raise ImageGenerationError(f"Unexpected Stability response: keys={list(data.keys()) if isinstance(data, dict) else type(data)}")
        
        # Handle data URI format
        if "," in b64:
            b64 = b64.split(",", 1)[1]
        
        return base64.b64decode(b64)
    
    def _stability_txt2img(self, panel: PanelSpec, base_url: str) -> bytes:
        """
        Generate image using Stability AI txt2img API.
        Supports both engines and images API modes.
        
        Returns:
            Raw PNG bytes from Stability API
        """
        # Check available balance before proceeding
        balance = self._get_stability_balance()
        if balance is not None and balance < 0.009:
            logger.warning(f"Low Stability API balance: ${balance:.6f}. Txt2img typically costs $0.008-0.009")
            # Don't fail immediately - let API reject if needed
        
        w = panel.sdxl_hints.width or self.config["width"]
        h = panel.sdxl_hints.height or self.config["height"]
        guidance = panel.sdxl_hints.cfg_scale or self.config["stability_guidance"]
        steps = panel.sdxl_hints.steps or self.config["stability_steps"]
        model = getattr(panel.sdxl_hints, "model", None) or self.config["stability_model"]
        
        mode = self.config["stability_mode"]
        
        if mode == "engines":
            # Snap dimensions to SDXL 1.0 allowed sizes
            w, h = _snap_to_sdxl10_allowed(w, h)
            
            # Engines API: /v1/generation/{engine}/text-to-image
            path = self.config["stability_txt2img_path"].format(engine=model)
            url = f"{base_url.rstrip('/')}{path}"

            pos = panel.positive_prompt or ""
            neg = (panel.negative_prompt or "").strip()
            text_prompts = [{"text": pos, "weight": 1.0}]
            if neg:
                text_prompts.append({"text": neg, "weight": -1.0})

            payload = {
                "text_prompts": text_prompts,
                "cfg_scale": guidance,
                "height": h, 
                "width": w,
                "samples": 1,
                "steps": steps,
                "seed": panel.sdxl_hints.seed or None,
                # optional: "clip_guidance_preset": "FAST_BLUE"
            }
            
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}
            
            headers = self._stability_headers()

            try:
                # Small delay to avoid rate limiting
                time.sleep(0.5)
                r = requests.post(url, headers=headers, json=payload, timeout=settings.http_timeout)
                r.raise_for_status()
                return self._stability_extract_b64(r.json())
            except requests.HTTPError as e:
                body = getattr(e.response, "text", "")
                logger.error("Stability engines txt2img failed: %s\nPayload:\n%s\nResponse:\n%s",
                             e, json.dumps(payload, indent=2)[:2000], body[:2000])
                raise
            
        else:  # "images" mode - v2beta API with multipart/form-data
            path = self.config["stability_txt2img_path"]
            url = f"{base_url.rstrip('/')}{path}"
            
            w = panel.sdxl_hints.width or self.config["width"]
            h = panel.sdxl_hints.height or self.config["height"]
            
            # v2beta API uses form data, not JSON
            data = {
                "model": self.config["stability_model"],  # sd3.5-large-turbo
                "prompt": panel.positive_prompt or "",
                "width": str(w),
                "height": str(h),
                "steps": str(panel.sdxl_hints.steps or self.config["stability_steps"]),
                "cfg_scale": str(panel.sdxl_hints.cfg_scale or self.config["stability_guidance"]),
            }
            
            # Add optional parameters
            neg_prompt = (panel.negative_prompt or "").strip()
            if neg_prompt:
                data["negative_prompt"] = neg_prompt
                
            if panel.sdxl_hints.seed:
                data["seed"] = str(panel.sdxl_hints.seed)
            
            # v2beta API expects image/* Accept header and multipart form data
            headers = {
                "Authorization": f"Bearer {settings.stability_api_key}",
                "Accept": "image/*"
            }
            
            # Force multipart/form-data by including empty files dict
            files = {'none': (None, '')}
            
            try:
                # Small delay to avoid rate limiting
                time.sleep(0.5)
                r = requests.post(url, headers=headers, data=data, files=files, timeout=settings.http_timeout)
                r.raise_for_status()
                
                # v2beta API returns image data directly
                return r.content
                
            except requests.HTTPError as e:
                logger.error("Stability v2beta txt2img failed: %s\nData:\n%s\nResponse:\n%s",
                             e, json.dumps(data, indent=2)[:2000], getattr(e.response, "text", "")[:2000])
                raise
    
    def _stability_img2img(self, panel: PanelSpec, base_url: str, ref_path: str) -> bytes:
        """
        Generate image using Stability AI img2img API with reference image.
        Supports both engines and images API modes.
        
        Returns:
            Raw PNG bytes from Stability API
        """
        w = panel.sdxl_hints.width or self.config["width"]
        h = panel.sdxl_hints.height or self.config["height"]
        guidance = panel.sdxl_hints.cfg_scale or self.config["stability_guidance"]
        steps = panel.sdxl_hints.steps or self.config["stability_steps"]
        model = getattr(panel.sdxl_hints, "model", None) or self.config["stability_model"]
        
        # Strength mapping for continuity
        strength = min(max(panel.reference.strength_hint or 0.6, 0.1), 0.95)
        
        mode = self.config["stability_mode"]
        
        if mode == "engines":
            # For engines API, dimensions come from input image, no snapping needed
            
            # Engines API: /v1/generation/{engine}/image-to-image
            path = self.config["stability_img2img_path"].format(engine=model)
            url = f"{base_url.rstrip('/')}{path}"

            pos = panel.positive_prompt or ""
            neg = (panel.negative_prompt or "").strip()

            files = {"init_image": open(ref_path, "rb")}
            data = {
                "text_prompts[0][text]": pos,
                "text_prompts[0][weight]": "1.0",
                "cfg_scale": str(guidance),
                # Note: height/width not allowed for img2img in engines API
                "samples": "1",
                "steps": str(steps),
                "image_strength": str(strength),
                "seed": str(panel.sdxl_hints.seed or 0),
            }
            
            # Add negative prompt as second text_prompts entry if provided
            if neg:
                data["text_prompts[1][text]"] = neg
                data["text_prompts[1][weight]"] = "-1.0"

            try:
                # Small delay to avoid rate limiting
                time.sleep(0.5)
                r = requests.post(url, headers=self._stability_headers(), data=data, files=files, timeout=settings.http_timeout)
                r.raise_for_status()
                return self._stability_extract_b64(r.json())
            except requests.HTTPError as e:
                body = getattr(e.response, "text", "")
                logger.error("Stability engines img2img failed: %s\nForm-data:\n%s\nResponse:\n%s",
                             e, json.dumps({**data, "init_image":"<binary>"}, indent=2)[:2000], body[:2000])
                raise
            finally:
                files["init_image"].close()
                
        else:  # "images" mode - v2beta API with image-to-image mode
            path = self.config["stability_img2img_path"]
            url = f"{base_url.rstrip('/')}{path}"
            
            w = panel.sdxl_hints.width or self.config["width"]
            h = panel.sdxl_hints.height or self.config["height"]
            strength = min(max(panel.reference.strength_hint or 0.6, 0.1), 0.95)

            files = {"image": open(ref_path, "rb")}
            data = {
                "mode": "image-to-image",  # Required for v2beta img2img
                "model": self.config["stability_model"],  # sd3.5-large-turbo
                "prompt": panel.positive_prompt or "",
                "width": str(w),
                "height": str(h),
                "steps": str(panel.sdxl_hints.steps or self.config["stability_steps"]),
                "cfg_scale": str(panel.sdxl_hints.cfg_scale or self.config["stability_guidance"]),
                "strength": str(strength),
            }
            
            # Add optional parameters
            neg_prompt = (panel.negative_prompt or "").strip()
            if neg_prompt:
                data["negative_prompt"] = neg_prompt
                
            if panel.sdxl_hints.seed:
                data["seed"] = str(panel.sdxl_hints.seed)
            
            # v2beta API expects image/* Accept header
            headers = {
                "Authorization": f"Bearer {settings.stability_api_key}",
                "Accept": "image/*"
            }

            try:
                # Small delay to avoid rate limiting
                time.sleep(0.5)
                r = requests.post(url, headers=headers, data=data, files=files, timeout=settings.http_timeout)
                r.raise_for_status()
                
                # v2beta API returns image data directly
                return r.content
                
            except requests.HTTPError as e:
                logger.error("Stability v2beta img2img failed: %s\nData:\n%s\nResponse:\n%s",
                             e, json.dumps({**data, "image":"<binary>"}, indent=2)[:2000], getattr(e.response, "text", "")[:2000])
                raise
            finally:
                files["image"].close()
    
    def _generate_stability(
        self,
        panel: PanelSpec,
        output_path: Path,
        reference_image_path: Optional[str] = None
    ) -> str:
        """Generate image using Stability AI API."""
        
        base_url = self.config["stability_url"]
        
        try:
            if panel.reference.use_previous_image and reference_image_path:
                logger.info(f"Generating Stability img2img for panel {panel.chunk_id}")
                raw = self._stability_img2img(panel, base_url, reference_image_path)
            else:
                logger.info(f"Generating Stability txt2img for panel {panel.chunk_id}")
                raw = self._stability_txt2img(panel, base_url)
            
            # Save the image
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(raw)
            
            logger.info(f"Generated Stability image: {output_path} ({len(raw)} bytes)")
            return str(output_path.resolve()).replace("\\", "/")
            
        except Exception as e:
            logger.error(f"Stability generation failed for panel {panel.chunk_id}: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Stability API response: {e.response.text}")
            # Graceful fallback to enhanced placeholder
            return self._generate_placeholder(output_path, label=panel.caption or "stability-fallback")
    
    def _generate_comfyui(
        self,
        panel: PanelSpec,
        output_path: Path,
        reference_image_path: Optional[str] = None
    ) -> str:
        """Generate image using ComfyUI (future implementation)."""
        
        logger.warning("ComfyUI backend not yet implemented, falling back to placeholder")
        return self._generate_placeholder(output_path, label=f"ComfyUI: {panel.chunk_id}")
    
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
                    Path(output_dir) / f"panel_{panel.chunk_id}_error.png",
                    label=f"Error: {panel.chunk_id}"
                )
                results[panel.chunk_id] = placeholder_path
        
        # Safety net: detect accidental placeholder fallbacks
        if results:
            sizes = {Path(p).stat().st_size for p in results.values()}
            if len(sizes) == 1:
                single_size = list(sizes)[0]
                if single_size < 50000:  # Less than 50KB suggests placeholders
                    if settings.image_backend == "stability":
                        logger.warning("All panels identical small size — likely Stability API fallback to placeholders. Check API key/endpoints.")
                    elif self.backend == "sdxl-a1111":
                        logger.warning("All panels identical size — likely placeholder fallback or failed A1111 calls.")
                    else:
                        logger.warning(f"All panels identical small size ({single_size} bytes) — check {self.backend} configuration.")
        
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
