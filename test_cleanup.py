#!/usr/bin/env python3
"""Test script to verify all cleanup improvements."""

import logging
from src.agentic_flow.image_service import ImageService
from src.agentic_flow.image_continuity_evaluator import get_lpips_model, LPIPS_AVAILABLE

logging.basicConfig(level=logging.INFO)

def test_cleanup_improvements():
    """Test all cleanup improvements."""
    print("=== Testing StAnify Cleanup Improvements ===")
    
    # Test image service backend selection
    service = ImageService()
    print(f"Active backend: {service._active_backend}")
    print(f"Backend config: {service.config.get('backend', 'not set')}")
    
    # Test LPIPS singleton (should only load once)
    if LPIPS_AVAILABLE:
        print("\n=== LPIPS Singleton Test ===")
        model1 = get_lpips_model()
        model2 = get_lpips_model()
        print(f"LPIPS model 1 ID: {id(model1) if model1 else 'None'}")
        print(f"LPIPS model 2 ID: {id(model2) if model2 else 'None'}")
        print(f"Same instance: {model1 is model2}")
    else:
        print("LPIPS not available for testing")
    
    # Test regeneration setting
    print("\n=== Pipeline Configuration ===")
    from src.agentic_flow.pipeline import run_demo
    import inspect
    source = inspect.getsource(run_demo)
    if "max_regenerations = 1" in source:
        print("✅ Regeneration re-enabled (max_regenerations = 1)")
    elif "max_regenerations = 0" in source:
        print("❌ Regeneration still disabled (max_regenerations = 0)")
    else:
        print("⚠️ Could not detect regeneration setting")
    
    print("\n=== Cleanup Improvements Test Complete ===")

if __name__ == "__main__":
    test_cleanup_improvements()
