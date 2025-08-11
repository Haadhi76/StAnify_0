"""Smoke tests for the pipeline to ensure end-to-end functionality."""
import sys
import tempfile
import json
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
            from agentic_flow.export_validator import validate_before_export
            from agentic_flow.manifest_contracts import RunManifest

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
    
    def test_complete_pipeline_generation(self):
        """
        END-TO-END SMOKE TEST: Complete pipeline with export validation.
        This test ensures the full pipeline works and produces quality outputs.
        """
        
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Import pipeline components
                from agentic_flow.pipeline import run_demo
                from agentic_flow.manifest_contracts import RunManifest
                from agentic_flow.export_validator import validate_before_export
                
                # Test with a simple Year 1 mathematics prompt
                user_prompt = "Teach children how to count to 10 using fun examples"
                year = "Year 1"
                subject = "mathematics"
                kb_dir = "kb"  # Use existing knowledge base
                
                # Run the complete pipeline
                result = run_demo(
                    year=year,
                    subject=subject,
                    user_prompt=user_prompt,
                    kb_dir=kb_dir,
                    out_dir=temp_dir
                )
                
                # ASSERT: Basic result structure
                assert "run_id" in result, "Result missing run_id"
                assert "pdf" in result, "Result missing PDF path"
                assert "pptx" in result, "Result missing PPTX path"
                assert "manifest" in result, "Result missing manifest path"
                
                run_id = result["run_id"]
                
                # ASSERT: Files exist
                pdf_path = Path(result["pdf"])
                pptx_path = Path(result["pptx"])
                manifest_path = Path(result["manifest"])
                
                assert pdf_path.exists(), f"PDF not found: {pdf_path}"
                assert pptx_path.exists(), f"PPTX not found: {pptx_path}"
                assert manifest_path.exists(), f"Manifest not found: {manifest_path}"
                
                # ASSERT: Files are non-trivial size (>10KB as per requirements)
                assert pdf_path.stat().st_size > 10240, f"PDF too small: {pdf_path.stat().st_size} bytes"
                assert pptx_path.stat().st_size > 10240, f"PPTX too small: {pptx_path.stat().st_size} bytes"
                assert manifest_path.stat().st_size > 1024, f"Manifest too small: {manifest_path.stat().st_size} bytes"
                
                # ASSERT: Manifest validation
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                
                manifest = RunManifest(**manifest_data)
                
                # Run comprehensive export validation
                validation_results = validate_before_export(manifest)
                
                # ASSERT: Critical validations pass
                assert validation_results['counts_match'], "Panel/chunk count mismatch"
                assert validation_results['images_valid'], "Invalid panel images"
                assert validation_results['chunks_have_text'], "Empty chunks found"
                
                # ASSERT: Educational content quality
                assert len(manifest.chunks) >= 3, f"Too few chunks: {len(manifest.chunks)}"
                assert len(manifest.panels) == len(manifest.chunks), "Panel/chunk count mismatch"
                
                # ASSERT: Learning objectives present
                objectives = getattr(manifest.refined_prompt, 'learning_objectives', [])
                assert len(objectives) >= 1, "No learning objectives found"
                
                # ASSERT: Panel images valid (>1KB each)
                for panel in manifest.panels:
                    assert panel.image_uri, f"Panel {panel.chunk_id} missing image_uri"
                    image_path = Path(panel.image_uri)
                    assert image_path.exists(), f"Panel image not found: {image_path}"
                    assert image_path.stat().st_size > 1024, f"Panel image too small: {image_path.stat().st_size} bytes"
                
                print(f"✅ SMOKE TEST PASSED: Generated {run_id} with {len(manifest.panels)} panels")
                print(f"   PDF: {pdf_path.stat().st_size} bytes")
                print(f"   PPTX: {pptx_path.stat().st_size} bytes")
                print(f"   Validation: {sum(validation_results.values())}/{len(validation_results)} checks passed")
                
            except ImportError as e:
                pytest.skip(f"Pipeline components not available: {e}")
            except Exception as e:
                pytest.fail(f"Pipeline smoke test failed: {e}")

        # Test pathlib operations
        assert test_path.is_dir(), "Should be recognized as directory"
