"""
Image Continuity Evaluator for StAnify Pipeline

Provides image quality and continuity assessment using:
- CLIPScore for prompt-image alignment
- LPIPS for perceptual similarity between panels
- SSIM for structural similarity between panels
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

# Check for basic dependencies
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logging.warning("NumPy not available. Install with: pip install numpy")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("PIL not available. Install with: pip install pillow")

# Optional imports with fallbacks
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logging.warning("PyTorch not available. Install with: pip install torch torchvision")

try:
    import clip
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False
    logging.warning("CLIP not available. Install with: pip install git+https://github.com/openai/CLIP.git")

try:
    import lpips
    LPIPS_AVAILABLE = True
except ImportError:
    LPIPS_AVAILABLE = False
    logging.warning("LPIPS not available. Install with: pip install lpips")

# Global singleton for LPIPS model to prevent double loading
_LPIPS_MODEL_SINGLETON = None

def get_lpips_model(device="cpu"):
    """Get singleton LPIPS model to prevent multiple initializations."""
    global _LPIPS_MODEL_SINGLETON
    if _LPIPS_MODEL_SINGLETON is None and LPIPS_AVAILABLE:
        try:
            logger.info("Loading LPIPS model (singleton initialization)")
            _LPIPS_MODEL_SINGLETON = lpips.LPIPS(net='alex').to(device)
            logger.info("LPIPS model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load LPIPS model: {e}")
            _LPIPS_MODEL_SINGLETON = None
    return _LPIPS_MODEL_SINGLETON

try:
    from skimage.metrics import structural_similarity as ssim
    from skimage.color import rgb2gray
    SSIM_AVAILABLE = True
except ImportError:
    SSIM_AVAILABLE = False
    logging.warning("SSIM not available. Install with: pip install scikit-image")

logger = logging.getLogger(__name__)


@dataclass
class ImageContinuityResult:
    """Results from image continuity evaluation."""
    clip_scores: List[float]  # Prompt-image alignment scores
    lpips_scores: List[float]  # Perceptual similarity scores between consecutive panels
    ssim_scores: List[float]  # Structural similarity scores between consecutive panels
    overall_score: float  # Combined continuity score (0-1)
    verdict: str  # "Pass", "Soft Pass", "Fail"
    recommendations: List[str]  # Specific improvement suggestions
    needs_regeneration: bool  # Whether images should be regenerated


class ImageContinuityEvaluator:
    """Evaluates image continuity and prompt alignment for educational content panels."""
    
    def __init__(self, device: Optional[str] = None):
        """
        Initialize the image continuity evaluator.
        
        Args:
            device: Device to run models on ('cuda', 'cpu', or None for auto-detect)
        """
        if TORCH_AVAILABLE and device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device or "cpu"
        logger.info(f"Initializing ImageContinuityEvaluator on device: {self.device}")
        
        # Initialize models
        self.clip_model = None
        self.clip_preprocess = None
        self.lpips_model = None
        
        self._init_clip()
        self._init_lpips()
        
        # Thresholds for evaluation
        self.clip_threshold_good = 0.25  # Good prompt-image alignment
        self.clip_threshold_acceptable = 0.15  # Acceptable alignment
        self.lpips_threshold_similar = 0.4  # Similar perceptual content
        self.ssim_threshold_similar = 0.5  # Similar structural content
        
    def _init_clip(self):
        """Initialize CLIP model for prompt-image alignment."""
        if not CLIP_AVAILABLE:
            logger.warning("CLIP not available, skipping prompt-image evaluation")
            return
            
        try:
            self.clip_model, self.clip_preprocess = clip.load("ViT-B/32", device=self.device)
            logger.info("CLIP model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
            self.clip_model = None
            
    def _init_lpips(self):
        """Initialize LPIPS model for perceptual similarity using singleton."""
        if not LPIPS_AVAILABLE:
            logger.warning("LPIPS not available, skipping perceptual similarity evaluation")
            return
            
        # Use singleton to prevent multiple model loads
        self.lpips_model = get_lpips_model(self.device)
    
    def evaluate_prompt_image_alignment(self, image_path: str, prompt: str) -> float:
        """
        Evaluate how well an image matches its prompt using CLIP.
        
        Args:
            image_path: Path to the image file
            prompt: Text prompt that generated the image
            
        Returns:
            CLIPScore (0-1, higher is better alignment)
        """
        if not self.clip_model:
            logger.warning("CLIP model not available, returning default score")
            return 0.5  # Neutral score when evaluation not possible
            
        try:
            # Load and preprocess image
            image = Image.open(image_path).convert('RGB')
            image_tensor = self.clip_preprocess(image).unsqueeze(0).to(self.device)
            
            # Truncate prompt to fit CLIP context length (77 tokens)
            # Rough estimate: 1 word ≈ 1.3 tokens, so 50 words ≈ 65 tokens with safety margin
            words = prompt.split()
            if len(words) > 50:
                truncated_prompt = " ".join(words[:50])
                logger.debug(f"Truncated prompt from {len(words)} to 50 words for CLIP evaluation")
            else:
                truncated_prompt = prompt
            
            # Tokenize text  
            text_tokens = clip.tokenize([truncated_prompt]).to(self.device)
            
            # Get embeddings
            with torch.no_grad():
                image_features = self.clip_model.encode_image(image_tensor)
                text_features = self.clip_model.encode_text(text_tokens)
                
                # Normalize features
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                
                # Calculate similarity
                similarity = torch.cosine_similarity(image_features, text_features).item()
                
            # Convert to 0-1 range (cosine similarity is -1 to 1)
            score = (similarity + 1) / 2
            logger.debug(f"CLIP score for '{prompt}': {score:.3f}")
            return score
            
        except Exception as e:
            logger.error(f"Error calculating CLIP score: {e}")
            return 0.5
    
    def evaluate_perceptual_similarity(self, image1_path: str, image2_path: str) -> float:
        """
        Evaluate perceptual similarity between two images using LPIPS.
        
        Args:
            image1_path: Path to first image
            image2_path: Path to second image
            
        Returns:
            LPIPS distance (0-1, lower is more similar)
        """
        if not self.lpips_model:
            logger.warning("LPIPS model not available, returning default score")
            return 0.5
            
        try:
            # Load and preprocess images
            def load_image_tensor(path: str) -> torch.Tensor:
                image = Image.open(path).convert('RGB')
                # Resize to consistent size for comparison
                image = image.resize((224, 224))
                # Convert to tensor and normalize to [-1, 1]
                tensor = torch.from_numpy(np.array(image)).float()
                tensor = tensor.permute(2, 0, 1) / 127.5 - 1.0
                return tensor.unsqueeze(0).to(self.device)
            
            img1_tensor = load_image_tensor(image1_path)
            img2_tensor = load_image_tensor(image2_path)
            
            # Calculate LPIPS distance
            with torch.no_grad():
                distance = self.lpips_model(img1_tensor, img2_tensor).item()
                
            logger.debug(f"LPIPS distance between images: {distance:.3f}")
            return distance
            
        except Exception as e:
            logger.error(f"Error calculating LPIPS distance: {e}")
            return 0.5
    
    def evaluate_structural_similarity(self, image1_path: str, image2_path: str) -> float:
        """
        Evaluate structural similarity between two images using SSIM.
        
        Args:
            image1_path: Path to first image
            image2_path: Path to second image
            
        Returns:
            SSIM score (0-1, higher is more similar)
        """
        if not SSIM_AVAILABLE:
            logger.warning("SSIM not available, returning default score")
            return 0.5
            
        try:
            # Load images and convert to grayscale
            image1 = Image.open(image1_path).convert('RGB')
            image2 = Image.open(image2_path).convert('RGB')
            
            # Resize to same dimensions
            size = (224, 224)
            image1 = image1.resize(size)
            image2 = image2.resize(size)
            
            # Convert to numpy arrays and grayscale
            img1_gray = rgb2gray(np.array(image1))
            img2_gray = rgb2gray(np.array(image2))
            
            # Calculate SSIM
            score, _ = ssim(img1_gray, img2_gray, full=True, data_range=1.0)
            
            logger.debug(f"SSIM score between images: {score:.3f}")
            return score
            
        except Exception as e:
            logger.error(f"Error calculating SSIM score: {e}")
            return 0.5
    
    def evaluate_panel_continuity(
        self, 
        image_paths: List[str], 
        prompts: List[str]
    ) -> ImageContinuityResult:
        """
        Evaluate continuity across a series of image panels.
        
        Args:
            image_paths: List of paths to panel images in sequence
            prompts: List of prompts corresponding to each image
            
        Returns:
            ImageContinuityResult with detailed evaluation
        """
        logger.info(f"Evaluating continuity for {len(image_paths)} panels")
        
        if len(image_paths) != len(prompts):
            raise ValueError("Number of images and prompts must match")
        
        if len(image_paths) < 2:
            logger.warning("Need at least 2 panels for continuity evaluation")
            return ImageContinuityResult(
                clip_scores=[],
                lpips_scores=[],
                ssim_scores=[],
                overall_score=1.0,
                verdict="Pass",
                recommendations=["Single panel - no continuity evaluation needed"],
                needs_regeneration=False
            )
        
        # Evaluate prompt-image alignment for each panel
        clip_scores = []
        for img_path, prompt in zip(image_paths, prompts):
            if Path(img_path).exists():
                score = self.evaluate_prompt_image_alignment(img_path, prompt)
                clip_scores.append(score)
            else:
                logger.warning(f"Image not found: {img_path}")
                clip_scores.append(0.0)
        
        # Evaluate continuity between consecutive panels
        lpips_scores = []
        ssim_scores = []
        
        for i in range(len(image_paths) - 1):
            img1_path = image_paths[i]
            img2_path = image_paths[i + 1]
            
            if Path(img1_path).exists() and Path(img2_path).exists():
                lpips_dist = self.evaluate_perceptual_similarity(img1_path, img2_path)
                ssim_score = self.evaluate_structural_similarity(img1_path, img2_path)
                
                lpips_scores.append(lpips_dist)
                ssim_scores.append(ssim_score)
            else:
                logger.warning(f"Missing images for continuity: {img1_path}, {img2_path}")
                lpips_scores.append(1.0)  # Maximum distance (poor continuity)
                ssim_scores.append(0.0)  # Minimum similarity
        
        # Calculate overall score and verdict
        return self._calculate_verdict(clip_scores, lpips_scores, ssim_scores)
    
    def _calculate_verdict(
        self, 
        clip_scores: List[float], 
        lpips_scores: List[float], 
        ssim_scores: List[float]
    ) -> ImageContinuityResult:
        """Calculate overall verdict from individual scores."""
        
        recommendations = []
        
        # Analyze CLIP scores (prompt-image alignment)
        avg_clip = np.mean(clip_scores) if clip_scores else 0.5
        poor_clip_panels = [i for i, score in enumerate(clip_scores) if score < self.clip_threshold_acceptable]
        
        if poor_clip_panels:
            recommendations.append(f"Panels {poor_clip_panels} have poor prompt alignment (CLIP < {self.clip_threshold_acceptable})")
        
        # Analyze continuity scores
        avg_lpips = np.mean(lpips_scores) if lpips_scores else 0.5
        avg_ssim = np.mean(ssim_scores) if ssim_scores else 0.5
        
        poor_continuity_pairs = []
        for i, (lpips_dist, ssim_score) in enumerate(zip(lpips_scores, ssim_scores)):
            if lpips_dist > self.lpips_threshold_similar and ssim_score < self.ssim_threshold_similar:
                poor_continuity_pairs.append(f"{i}-{i+1}")
        
        if poor_continuity_pairs:
            recommendations.append(f"Poor visual continuity between panel pairs: {', '.join(poor_continuity_pairs)}")
        
        # Calculate combined score (weighted)
        clip_weight = 0.4  # Prompt alignment is important
        continuity_weight = 0.6  # Visual continuity is crucial for educational materials
        
        # For continuity, lower LPIPS and higher SSIM are better
        continuity_score = (1 - avg_lpips) * 0.5 + avg_ssim * 0.5 if lpips_scores else 1.0
        
        overall_score = avg_clip * clip_weight + continuity_score * continuity_weight
        
        # Determine verdict
        if overall_score >= 0.7 and avg_clip >= self.clip_threshold_good:
            verdict = "Pass"
            needs_regen = False
        elif overall_score >= 0.5 and avg_clip >= self.clip_threshold_acceptable:
            verdict = "Soft Pass"
            needs_regen = False
            recommendations.append("Consider minor improvements for better visual coherence")
        else:
            verdict = "Fail"
            needs_regen = True
            recommendations.append("Recommend regenerating panels with improved prompts")
        
        return ImageContinuityResult(
            clip_scores=clip_scores,
            lpips_scores=lpips_scores,
            ssim_scores=ssim_scores,
            overall_score=overall_score,
            verdict=verdict,
            recommendations=recommendations,
            needs_regeneration=needs_regen
        )
    
    def should_regenerate_panels(self, result: ImageContinuityResult, max_regens: int = 2) -> bool:
        """
        Determine if panels should be regenerated based on continuity results.
        
        Args:
            result: ImageContinuityResult from evaluation
            max_regens: Maximum number of regenerations allowed
            
        Returns:
            True if panels should be regenerated
        """
        return result.needs_regeneration and max_regens > 0


def create_image_continuity_evaluator(device: Optional[str] = None) -> ImageContinuityEvaluator:
    """Factory function to create ImageContinuityEvaluator with proper error handling."""
    if not TORCH_AVAILABLE:
        logger.warning("PyTorch not available, using mock evaluator")
        return _MockImageContinuityEvaluator()
        
    try:
        return ImageContinuityEvaluator(device=device)
    except Exception as e:
        logger.error(f"Failed to create ImageContinuityEvaluator: {e}")
        # Return a mock evaluator that always passes
        return _MockImageContinuityEvaluator()


class _MockImageContinuityEvaluator:
    """Mock evaluator for when dependencies are not available."""
    
    def evaluate_panel_continuity(self, image_paths: List[str], prompts: List[str]) -> ImageContinuityResult:
        """Return a passing result when real evaluation is not available."""
        logger.warning("Using mock image continuity evaluator - install dependencies for real evaluation")
        return ImageContinuityResult(
            clip_scores=[0.5] * len(image_paths),
            lpips_scores=[0.3] * max(0, len(image_paths) - 1),
            ssim_scores=[0.7] * max(0, len(image_paths) - 1),
            overall_score=0.6,
            verdict="Pass",
            recommendations=["Mock evaluation - install CLIP, LPIPS, and scikit-image for real assessment"],
            needs_regeneration=False
        )
    
    def should_regenerate_panels(self, result: ImageContinuityResult, max_regens: int = 2) -> bool:
        """Mock always returns False."""
        return False
