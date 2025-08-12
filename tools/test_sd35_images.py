#!/usr/bin/env python3
"""
Quick smoke test script for SD3.5 Large Turbo via Images API.
Tests both text-to-image and image-to-image workflows.
"""

import os
import base64
import json
from pathlib import Path
import requests

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed, using OS environment only")

BASE = os.getenv("STABILITY_BASE_URL", "https://api.stability.ai")
KEY = os.getenv("STABILITY_API_KEY")
MODEL = os.getenv("STABILITY_MODEL", "sd3.5-large-turbo")

def test_sd35_images():
    """Test SD3.5 Large Turbo with Images API."""
    print("=== Testing SD3.5 Large Turbo Images API ===")
    print(f"Base URL: {BASE}")
    print(f"Model: {MODEL}")
    print(f"API Key: {'✅ Set' if KEY else '❌ Not Set'}")
    
    if not KEY:
        print("❌ STABILITY_API_KEY not found in environment")
        return
    
    headers = {"Authorization": f"Bearer {KEY}", "Accept": "image/*"}
    
    # Ensure exports directory exists
    Path("exports").mkdir(exist_ok=True)
    
    # Text-to-image test
    print("\n1. Testing txt2img...")
    url = f"{BASE}/v2beta/stable-image/generate/sd3"
    data = {
        "model": MODEL,
        "prompt": "cute, child-friendly classroom illustration, primary colors, simple shapes, high contrast",
        "width": "1024", 
        "height": "1024", 
        "steps": "28", 
        "cfg_scale": "6.5",
    }
    
    try:
        print(f"   Making request to: {url}")
        # Use multipart form data for v2beta API
        files = {'none': (None, '')}  # Dummy file entry to force multipart
        r = requests.post(url, headers={"Authorization": f"Bearer {KEY}", "Accept": "image/*"}, 
                         data=data, files=files, timeout=180)
        print(f"   Response status: {r.status_code}")
        
        if r.status_code != 200:
            print(f"   Error response: {r.text[:500]}")
        
        r.raise_for_status()
        
        # v2beta returns image directly
        img_bytes = r.content
        Path("exports/_sd35_t2i.png").write_bytes(img_bytes)
        print(f"✅ txt2img success: {len(img_bytes)} bytes -> exports/_sd35_t2i.png")
        
    except Exception as e:
        print(f"❌ txt2img failed: {e}")
        return

    # Image-to-image test (uses previous result)
    print("\n2. Testing img2img...")
    files = {"image": open("exports/_sd35_t2i.png", "rb")}
    data = {
        "mode": "image-to-image",
        "model": MODEL,
        "prompt": "same scene, add a child pointing to a number line; keep the same style",
        "width": "1024", 
        "height": "1024",
        "steps": "22", 
        "cfg_scale": "6.0", 
        "strength": "0.6",
    }
    
    url2 = f"{BASE}/v2beta/stable-image/generate/sd3"
    
    try:
        print(f"   Making request to: {url2}")
        r2 = requests.post(url2, headers={"Authorization": f"Bearer {KEY}", "Accept": "image/*"}, 
                          data=data, files=files, timeout=180)
        print(f"   Response status: {r2.status_code}")
        
        # If 400 error, show details
        if r2.status_code == 400:
            print("  API parameter error, checking response...")
            print(f"  Error details: {r2.text[:200]}")
        
        r2.raise_for_status()
        
        # v2beta returns image directly
        img2_bytes = r2.content
        Path("exports/_sd35_i2i.png").write_bytes(img2_bytes)
        print(f"✅ img2img success: {len(img2_bytes)} bytes -> exports/_sd35_i2i.png")
        
    except Exception as e:
        print(f"❌ img2img failed: {e}")
    finally:
        files["image"].close()
    
    print("\n=== SD3.5 Large Turbo Test Complete ===")

if __name__ == "__main__":
    test_sd35_images()
