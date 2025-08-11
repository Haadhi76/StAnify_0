#!/usr/bin/env python3
"""Test script for surgical fixes."""

import logging
from src.agentic_flow.image_service import ImageService, _snap_to_sdxl10_allowed, _is_placeholder_or_disallowed
from src.agentic_flow.settings import settings

logging.basicConfig(level=logging.INFO)

def test_fixes():
    """Test all the surgical fixes."""
    print("=== Testing StAnify Surgical Fixes ===")
    
    # Test basic initialization
    service = ImageService()
    print(f"Active backend: {service._active_backend}")
    print(f"Stability mode: {service.config.get('stability_mode', 'not set')}")
    
    # Test balance check if in stability mode
    if service._active_backend == 'stability':
        try:
            balance = service._get_stability_balance()
            if balance is not None:
                print(f"API Balance: ${balance:.6f}")
                if balance < 0.009:
                    print("WARNING: Low balance for txt2img operations")
            else:
                print("Balance check failed")
        except Exception as e:
            print(f"Balance check error: {e}")
    
    # Test dimension snapping
    test_dims = [(1024, 768), (512, 512), (1920, 1080)]
    print("\n=== Dimension Snapping Tests ===")
    for w, h in test_dims:
        snapped = _snap_to_sdxl10_allowed(w, h)
        print(f"{w}x{h} -> {snapped[0]}x{snapped[1]}")
    
    # Test placeholder detection
    print("\n=== Placeholder Detection Tests ===")
    test_files = [
        "assets/sample_panel.png",
        "exports/panel_c1.png",
        "nonexistent.png"
    ]
    for file_path in test_files:
        is_placeholder = _is_placeholder_or_disallowed(file_path)
        print(f"{file_path}: {'placeholder/disallowed' if is_placeholder else 'suitable for img2img'}")
    
    print("\n=== Fixes Test Complete ===")

if __name__ == "__main__":
    test_fixes()
