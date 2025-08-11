#!/usr/bin/env python3
"""Test API fixes for Cloudflare issues."""

import time
from src.agentic_flow.image_service import ImageService
from src.agentic_flow.image_panels_contracts import PanelSpec, SDXLHints

def test_api_fixes():
    """Test API fixes for rate limiting and Cloudflare issues."""
    print("=== Testing API Fixes ===")
    
    service = ImageService()
    
    # Test txt2img first (usually more reliable)
    panel = PanelSpec(
        chunk_id="test",
        index=0,
        positive_prompt="A simple red apple on a white background",
        negative_prompt="blurry, text",
        sdxl_hints=SDXLHints(
            width=1024,
            height=1024,
            cfg_scale=7.0,
            steps=20  # Reduced steps for faster testing
        )
    )
    
    try:
        print("Testing txt2img...")
        result = service._stability_txt2img(panel, service.config["stability_url"])
        if result and len(result) > 50000:  # At least 50KB
            print(f"✅ txt2img successful: {len(result)} bytes")
        else:
            print(f"❌ txt2img failed: {len(result) if result else 0} bytes")
    except Exception as e:
        print(f"❌ txt2img error: {e}")
    
    print("\n=== API Test Complete ===")

if __name__ == "__main__":
    test_api_fixes()
