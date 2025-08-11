#!/usr/bin/env python3
"""
Smoke test for Stability AI API integration.
Tests the Stability API endpoint and saves a test image.
"""

import os
import base64
import requests
from pathlib import Path

def test_stability_api():
    """Test basic Stability AI API functionality."""
    
    print("🧪 STABILITY AI API SMOKE TEST")
    print("=" * 40)
    
    # Get configuration from environment
    BASE_URL = os.getenv("STABILITY_BASE_URL", "https://api.stability.ai").rstrip("/")
    API_KEY = os.getenv("STABILITY_API_KEY")
    MODEL = os.getenv("STABILITY_MODEL", "stable-image-ultra")
    
    if not API_KEY:
        print("❌ Error: STABILITY_API_KEY environment variable not set")
        print("   Set it with: export STABILITY_API_KEY=sk-...")
        return False
    
    print(f"🔧 Base URL: {BASE_URL}")
    print(f"🤖 Model: {MODEL}")
    print(f"🔑 API Key: sk-...{API_KEY[-4:] if len(API_KEY) > 4 else 'SET'}")
    print()
    
    # Prepare test request
    headers = {"Authorization": f"Bearer {API_KEY}"}
    payload = {
        "model": MODEL,
        "prompt": "child-friendly classroom illustration, bright colors, simple shapes, educational, cartoon style",
        "negative_prompt": "text, watermark, gore, weapons, nsfw, dark, scary",
        "width": 512,
        "height": 384,
        "guidance": 7.0,
        "steps": 20
    }
    
    try:
        print("📡 Sending test request to Stability API...")
        url = f"{BASE_URL}/v1/images/generate"
        print(f"   URL: {url}")
        
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=120
        )
        
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            print(f"   Response: {response.text[:500]}...")
            return False
        
        # Parse response
        data = response.json()
        print(f"📋 Response keys: {list(data.keys())}")
        
        # Extract image data
        b64_image = None
        if "artifacts" in data and data["artifacts"]:
            artifact = data["artifacts"][0]
            print(f"   Artifact finish reason: {artifact.get('finishReason', 'unknown')}")
            b64_image = artifact.get("base64") or artifact.get("image")
        else:
            b64_image = data.get("image") or data.get("base64")
        
        if not b64_image:
            print("❌ Error: No image data found in response")
            print(f"   Response structure: {data}")
            return False
        
        # Handle data URI format
        if "," in b64_image:
            b64_image = b64_image.split(",", 1)[1]
        
        # Decode and save image
        image_data = base64.b64decode(b64_image)
        output_path = Path("exports/_smoke_stability.png")
        output_path.parent.mkdir(exist_ok=True)
        output_path.write_bytes(image_data)
        
        print(f"✅ Success! Generated test image:")
        print(f"   📁 File: {output_path}")
        print(f"   📏 Size: {len(image_data):,} bytes")
        print(f"   🎨 Resolution: {payload['width']}x{payload['height']}")
        
        return True
        
    except requests.exceptions.Timeout:
        print("❌ Error: Request timeout (API may be slow)")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: Request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_stability_api()
    exit(0 if success else 1)
