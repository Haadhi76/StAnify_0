#!/usr/bin/env python3
"""
Stability AI smoke test for StAnify
Tests the current configuration and generates a test image
"""

import os, base64, json
from pathlib import Path
import requests

BASE = os.getenv("STABILITY_BASE_URL", "https://api.stability.ai").rstrip("/")
MODE = os.getenv("STABILITY_API_MODE", "engines")
MODEL = os.getenv("STABILITY_MODEL", "stable-diffusion-xl-1024-v1-0")
KEY  = os.getenv("STABILITY_API_KEY")

if not KEY:
    print("❌ STABILITY_API_KEY not found in environment")
    exit(1)

print(f"🔧 Testing Stability AI Configuration")
print(f"   Base URL: {BASE}")
print(f"   Mode: {MODE}")
print(f"   Model: {MODEL}")
print(f"   Key: {'***' + KEY[-8:] if len(KEY) > 8 else '***'}")
print()

hdr = {"Authorization": f"Bearer {KEY}", "Accept":"application/json"}

try:
    if MODE == "engines":
        url = f"{BASE}/v1/generation/{MODEL}/text-to-image"
        payload = {
            "text_prompts": [{"text": "child-friendly classroom illustration", "weight": 1.0}],
            "cfg_scale": 7.0, "height": 896, "width": 1152, "samples": 1, "steps": 30
        }
        print(f"🚀 Calling engines API: {url}")
        print(f"   Payload: {json.dumps(payload, indent=2)}")
        
        r = requests.post(url, headers=hdr, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        b64 = data["artifacts"][0]["base64"]
        
    else:  # images mode
        url = f"{BASE}/v1/images/generate"
        payload = {
            "model": MODEL, "prompt": "child-friendly classroom illustration",
            "width": 1024, "height": 1024, "steps": 30, "guidance": 7.0
        }
        print(f"🚀 Calling images API: {url}")
        print(f"   Payload: {json.dumps(payload, indent=2)}")
        
        r = requests.post(url, headers=hdr, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        b64 = data.get("image") or data["images"][0]

    # Remove data URI prefix if present
    if "," in b64: 
        b64 = b64.split(",",1)[1]
    
    # Save image
    output_path = Path("exports/_smoke_stability.png")
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_bytes(base64.b64decode(b64))
    
    print(f"✅ SUCCESS: Generated image saved to {output_path}")
    print(f"   Size: {output_path.stat().st_size:,} bytes")
    print(f"   Response keys: {list(data.keys())}")
    
except requests.exceptions.HTTPError as e:
    print(f"❌ HTTP Error {e.response.status_code}: {e}")
    if hasattr(e, 'response') and e.response.text:
        print(f"   Response: {e.response.text[:500]}")
except Exception as e:
    print(f"❌ Error: {e}")
