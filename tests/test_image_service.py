"""
Tests for image service functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.agentic_flow.image_service import ImageService, generate_panel_image, generate_panel_batch
from src.agentic_flow.image_panels_contracts import (
    PanelSpec, ReferenceInstruction, SDXLHints, StyleCard, CharacterSpec
)
from src.agentic_flow.settings import settings


def create_test_panel(chunk_id: str = "test_chunk", use_previous: bool = False) -> PanelSpec:
    """Helper to create a valid PanelSpec for testing."""
    return PanelSpec(
        chunk_id=chunk_id,
        caption="Test caption",
        positive_prompt="Test prompt",
        negative_prompt="Test negative",
        reference=ReferenceInstruction(use_previous_image=use_previous),
        continuity_notes=["test"],
        style_card=StyleCard(
            render_style="test style",
            palette=["blue", "green"],
            camera="front view",
            aspect_ratio="4:3",
            character_sheet=[CharacterSpec(name="test_char")]
        ),
        sdxl_hints=SDXLHints()
    )


class TestImageService:
    """Test image service functionality."""
    
    def test_image_service_init(self):
        """Test image service initialization."""
        service = ImageService()
        assert service.backend == settings.image_backend
        assert service.config is not None
    
    def test_placeholder_generation(self):
        """Test placeholder image generation."""
        service = ImageService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_panel.png"
            
            result = service._generate_placeholder(output_path)
            
            assert output_path.exists()
            assert result == str(output_path.resolve())
    
    def test_simple_placeholder_creation(self):
        """Test simple placeholder creation when no sample exists."""
        service = ImageService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "simple_panel.png"
            
            # Mock missing sample file
            with patch.object(Path, 'exists', return_value=False):
                service._create_simple_placeholder(output_path)
            
            assert output_path.exists()
            assert output_path.stat().st_size > 0  # Should have content
    
    def test_generate_panel_image_placeholder_backend(self):
        """Test panel image generation with placeholder backend."""
        service = ImageService()
        service.backend = "placeholder"
        
        panel = create_test_panel()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = service.generate_panel_image(panel, temp_dir)
            
            assert Path(result).exists()
            assert "test_chunk" in result
    
    def test_generate_panel_batch(self):
        """Test batch panel generation."""
        service = ImageService()
        service.backend = "placeholder"
        
        panels = [
            create_test_panel("c1", use_previous=False),
            create_test_panel("c2", use_previous=True)
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            results = service.generate_panel_batch(panels, temp_dir)
            
            assert len(results) == 2
            assert "c1" in results
            assert "c2" in results
            assert Path(results["c1"]).exists()
            assert Path(results["c2"]).exists()
    
    def test_a1111_backend_fallback(self):
        """Test A1111 backend falls back to placeholder on error."""
        service = ImageService()
        service.backend = "sdxl-a1111"
        
        panel = create_test_panel()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock requests to raise exception
            with patch('src.agentic_flow.image_service.requests') as mock_requests:
                mock_requests.post.side_effect = Exception("Connection failed")
                
                result = service.generate_panel_image(panel, temp_dir)
                
                # Should fallback to placeholder
                assert Path(result).exists()
    
    def test_unknown_backend_fallback(self):
        """Test unknown backend falls back to placeholder."""
        service = ImageService()
        service.backend = "unknown_backend"
        
        panel = create_test_panel()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = service.generate_panel_image(panel, temp_dir)
            
            # Should fallback to placeholder
            assert Path(result).exists()
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        panel = create_test_panel()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test single panel function
            result = generate_panel_image(panel, temp_dir)
            assert Path(result).exists()
            
            # Test batch function
            batch_results = generate_panel_batch([panel], temp_dir)
            assert len(batch_results) == 1
            assert "test_chunk" in batch_results
