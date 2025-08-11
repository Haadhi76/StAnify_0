"""Tests for Pydantic contract validation - Basic Smoke Tests."""
import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentic_flow.chunks_contracts import ChunksOutput, ChunkSpec
from agentic_flow.critique_contracts import CritiqueScores
from agentic_flow.image_panels_contracts import (
    CharacterSpec,
    PanelSpec,
    ReferenceInstruction,
    StyleCard,
)

# Simple test data that meets minimum requirements
SAMPLE_CHUNK_SPEC_DATA = {
    "chunk_id": "test_chunk_001",
    "index": 0,
    "title": "Photosynthesis Introduction",
    "text": "Plants use sunlight to create energy through photosynthesis.",
    "goal": "Explain the basic concept of photosynthesis"
}


class TestBasicContractValidation:
    """Basic validation tests for key contracts."""

    def test_chunk_spec_minimal(self):
        """Test ChunkSpec with minimal required fields."""
        chunk = ChunkSpec.parse_obj(SAMPLE_CHUNK_SPEC_DATA)
        assert chunk.chunk_id == "test_chunk_001"
        assert chunk.index == 0
        assert "photosynthesis" in chunk.text

        # Test serialization
        chunk_dict = chunk.dict()
        assert chunk_dict["chunk_id"] == "test_chunk_001"

        chunk_json = chunk.json()
        assert "test_chunk_001" in chunk_json

    def test_chunks_output_minimal(self):
        """Test ChunksOutput with minimal data."""
        chunks_data = {
            "narrative": "This is a test narrative about photosynthesis.",
            "chunks": [SAMPLE_CHUNK_SPEC_DATA]
        }

        chunks_output = ChunksOutput.parse_obj(chunks_data)
        assert "photosynthesis" in chunks_output.narrative
        assert len(chunks_output.chunks) == 1
        assert chunks_output.chunks[0].chunk_id == "test_chunk_001"

    def test_character_spec_minimal(self):
        """Test CharacterSpec with minimal data."""
        character_data = {
            "name": "Plant Character"
        }

        character = CharacterSpec.parse_obj(character_data)
        assert character.name == "Plant Character"
        assert character.age is None  # Optional field

    def test_style_card_minimal(self):
        """Test StyleCard with minimal required fields."""
        style_data = {
            "render_style": "educational illustration",
            "palette": ["green", "yellow", "blue"],
            "camera": "front view",
            "aspect_ratio": "16:9"
        }

        style = StyleCard.parse_obj(style_data)
        assert style.render_style == "educational illustration"
        assert "green" in style.palette
        assert style.camera == "front view"
        assert style.aspect_ratio == "16:9"

    def test_reference_instruction_minimal(self):
        """Test ReferenceInstruction with minimal data."""
        ref_data = {
            "use_previous_image": False
        }

        reference = ReferenceInstruction.parse_obj(ref_data)
        assert reference.use_previous_image is False
        assert reference.purpose is None  # Optional
        assert reference.strength_hint is None  # Optional

    def test_critique_scores_minimal(self):
        """Test CritiqueScores with minimal data."""
        scores_data = {
            "alignment": 4,
            "vocab": 5,
            "scope": 3,
            "cognitive_load": 4
        }

        scores = CritiqueScores.parse_obj(scores_data)
        assert scores.alignment == 4
        assert scores.vocab == 5
        assert scores.scope == 3
        assert scores.cognitive_load == 4


class TestContractIntegration:
    """Test that contracts work together properly."""

    def test_full_panel_spec_creation(self):
        """Test creating a complete PanelSpec with all required fields."""
        # Create required sub-components first
        style_card_data = {
            "render_style": "educational illustration",
            "palette": ["green", "yellow", "blue"],
            "camera": "front view",
            "aspect_ratio": "16:9"
        }

        reference_data = {
            "use_previous_image": False
        }

        # Create the full panel spec
        panel_data = {
            "chunk_id": "chunk_001",
            "caption": "A plant absorbing sunlight",
            "positive_prompt": "Educational illustration of a green plant leaf with golden sunlight",
            "reference": reference_data,
            "style_card": style_card_data
        }

        panel = PanelSpec.parse_obj(panel_data)
        assert panel.chunk_id == "chunk_001"
        assert panel.caption == "A plant absorbing sunlight"
        assert "illustration" in panel.positive_prompt
        assert panel.style_card.render_style == "educational illustration"
        assert panel.reference.use_previous_image is False

    def test_import_all_contracts(self):
        """Test that all contract modules can be imported successfully."""
        # This test ensures all contract files are syntactically correct
        from agentic_flow import (
            chunks_contracts,
            critique_contracts,
            image_panels_contracts,
            manifest_contracts,
        )

        # Verify key classes exist
        assert hasattr(chunks_contracts, 'ChunkSpec')
        assert hasattr(image_panels_contracts, 'PanelSpec')
        assert hasattr(manifest_contracts, 'RunManifest')
        assert hasattr(critique_contracts, 'CritiqueOutput')


class TestErrorHandling:
    """Test error handling for contract validation."""

    def test_chunk_spec_missing_required_fields(self):
        """Test validation errors for missing required fields."""
        incomplete_data = {"chunk_id": "test"}  # Missing required fields

        with pytest.raises(Exception):  # Pydantic v1 validation error
            ChunkSpec.parse_obj(incomplete_data)

    def test_invalid_data_types(self):
        """Test validation errors for wrong data types."""
        invalid_data = SAMPLE_CHUNK_SPEC_DATA.copy()
        invalid_data["index"] = "not_a_number"  # Should be int

        with pytest.raises(Exception):  # Pydantic v1 validation error
            ChunkSpec.parse_obj(invalid_data)

    def test_style_card_empty_palette(self):
        """Test StyleCard validation with empty palette."""
        invalid_style_data = {
            "render_style": "illustration",
            "palette": [],  # Should have min_items=1
            "camera": "front view",
            "aspect_ratio": "16:9"
        }

        with pytest.raises(Exception):  # Pydantic v1 validation error
            StyleCard.parse_obj(invalid_style_data)
