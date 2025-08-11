"""Smoke tests for the pipeline to ensure end-to-end functionality."""
import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestPipelineSmoke:
    """Smoke tests for the complete pipeline."""

    def test_pipeline_imports(self):
        """Test that all pipeline components can be imported successfully."""
        try:
            from agentic_flow import kb_loader, pipeline
            from agentic_flow.exporters import pdf_exporter, pptx_exporter

            # Verify modules are not None
            assert pipeline is not None
            assert kb_loader is not None
            assert pdf_exporter is not None
            assert pptx_exporter is not None

        except ImportError as e:
            pytest.fail(f"Failed to import pipeline components: {str(e)}")

    def test_knowledge_base_loading(self):
        """Test that knowledge base files can be loaded successfully."""
        try:
            from pathlib import Path

            from agentic_flow.kb_loader import load_curriculum_kb

            # Get the kb directory path
            project_root = Path(__file__).parent.parent
            kb_path = project_root / "kb"

            # Load the curriculum knowledge base
            kb = load_curriculum_kb(str(kb_path))

            # Verify we got a knowledge base
            assert kb is not None, "Expected to load knowledge base"

            # Basic validation that it's a proper KB object
            assert hasattr(kb, '__dict__'), "KB should be a structured object"

        except Exception as e:
            pytest.fail(f"Knowledge base loading failed: {str(e)}")

    def test_demo_pipeline_callable(self):
        """Test that the demo pipeline function exists and is callable."""
        try:
            from agentic_flow.pipeline import run_demo

            # Verify the function exists
            assert callable(run_demo), "run_demo should be callable"

        except ImportError as e:
            pytest.fail(f"Could not import run_demo: {str(e)}")

    def test_exporters_have_required_functions(self):
        """Test that exporters have the expected function signatures."""
        try:
            from agentic_flow.exporters.pdf_exporter import export_manifest_to_pdf
            from agentic_flow.exporters.pptx_exporter import export_manifest_to_pptx

            # Verify functions exist
            assert callable(export_manifest_to_pdf), "export_manifest_to_pdf should be callable"
            assert callable(export_manifest_to_pptx), "export_manifest_to_pptx should be callable"

        except ImportError as e:
            pytest.fail(f"Could not import exporter functions: {str(e)}")

    def test_export_files_exist(self, project_root):
        """Test that some export files exist (indicating successful previous runs)."""
        # Check if the exports directory exists
        exports_dir = project_root / "exports"

        if not exports_dir.exists():
            pytest.skip("No exports directory found - pipeline may not have been run yet")

        # Look for any export files
        all_files = list(exports_dir.glob("*"))

        if len(all_files) == 0:
            pytest.skip("No export files found - pipeline may not have been run yet")

        # If we have files, check for expected types
        pdf_files = list(exports_dir.glob("*.pdf"))
        pptx_files = list(exports_dir.glob("*.pptx"))
        manifest_files = list(exports_dir.glob("*.manifest.json"))

        # Log what we found
        print(f"Found {len(pdf_files)} PDF files, {len(pptx_files)} PPTX files, {len(manifest_files)} manifest files")

        # At least some files should exist
        assert len(all_files) > 0, "Expected at least some export files"


class TestStreamlitAppImports:
    """Test that the Streamlit app can import correctly."""

    def test_streamlit_app_imports(self, project_root):
        """Test that the Streamlit app can import all necessary components."""
        streamlit_app_path = project_root / "streamlit_app" / "app.py"

        if not streamlit_app_path.exists():
            pytest.skip("Streamlit app not found")

        try:
            # Read the file to check for basic import structure
            app_content = streamlit_app_path.read_text()

            # Check for expected imports
            assert "streamlit" in app_content, "Should import streamlit"
            assert "from src.agentic_flow" in app_content, "Should import from agentic_flow"

        except Exception as e:
            pytest.fail(f"Streamlit app analysis failed: {str(e)}")


class TestAssetFiles:
    """Test that required asset files exist."""

    def test_sample_assets_exist(self, project_root):
        """Test that sample assets are available."""
        assets_dir = project_root / "assets"

        if not assets_dir.exists():
            pytest.skip("Assets directory not found")

        # Look for sample panel image
        sample_panel = assets_dir / "sample_panel.png"
        if sample_panel.exists():
            assert sample_panel.stat().st_size > 0, "Sample panel should not be empty"

    def test_knowledge_base_files_exist(self, project_root):
        """Test that knowledge base files are available."""
        kb_dir = project_root / "kb"

        assert kb_dir.exists(), "Knowledge base directory should exist"

        # Look for YAML files
        yaml_files = list(kb_dir.glob("*.yaml")) + list(kb_dir.glob("*.yml"))

        assert len(yaml_files) > 0, "Should have at least one knowledge base YAML file"

        # Check that files are not empty
        for yaml_file in yaml_files:
            assert yaml_file.stat().st_size > 0, f"{yaml_file.name} should not be empty"


class TestCrossCompatibility:
    """Test cross-platform compatibility features."""

    def test_path_handling(self, project_root):
        """Test that path handling works on current platform."""

        # Test basic path operations
        test_path = project_root / "src" / "agentic_flow"
        assert test_path.exists(), "Agentic flow directory should exist"

        # Test path string conversion
        path_str = str(test_path)
        assert len(path_str) > 0, "Path should convert to non-empty string"

        # Test pathlib operations
        assert test_path.is_dir(), "Should be recognized as directory"
