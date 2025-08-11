#!/usr/bin/env python3
"""
Quick sanity check for A1111 connection and model discovery.
Run this before starting StAnify to verify A1111 is ready.
"""

import requests
import json
import os
from datetime import datetime

def test_a1111_connection():
    """Test A1111 API connection and list available models."""
    
    base_url = os.getenv("A1111_BASE_URL", "http://127.0.0.1:7860")
    model_name = os.getenv("A1111_MODEL", "sdxl_base_1.0")
    
    print(f"🔍 Testing A1111 connection at {base_url}")
    print(f"📅 Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Looking for model: {model_name}")
    print("-" * 60)
    
    try:
        # Test basic connection
        print("1. Testing basic API connection...")
        r = requests.get(f"{base_url}/sdapi/v1/sd-models", timeout=10)
        r.raise_for_status()
        models = r.json()
        
        print(f"✅ A1111 online: {len(models)} models available")
        
        # List all available models
        print(f"\n2. Available models:")
        model_found = False
        for i, model in enumerate(models):
            title = model.get('title', 'Unknown')
            filename = model.get('filename', 'Unknown')
            print(f"   {i+1:2d}. {title}")
            if filename:
                print(f"       File: {filename}")
            
            # Check if our target model is available
            if model_name.lower() in title.lower():
                model_found = True
                print(f"       🎯 MATCH: This is our target model!")
        
        # Model availability check
        print(f"\n3. Target model check:")
        if model_found:
            print(f"✅ Target model '{model_name}' found!")
        else:
            print(f"⚠️  Target model '{model_name}' not found.")
            print(f"   Consider updating A1111_MODEL env var to one of the above.")
        
        # Test a simple generation (optional)
        print(f"\n4. Testing simple generation...")
        test_payload = {
            "prompt": "test image, simple",
            "negative_prompt": "blurry, bad quality",
            "width": 512,
            "height": 512,
            "steps": 10,
            "cfg_scale": 7.0,
            "sampler_name": "Euler a",
            "batch_size": 1,
            "n_iter": 1
        }
        
        # Add model override if we found it
        if model_found:
            test_payload["override_settings"] = {"sd_model_checkpoint": model_name}
        
        print(f"   Sending test generation request...")
        r = requests.post(f"{base_url}/sdapi/v1/txt2img", json=test_payload, timeout=30)
        r.raise_for_status()
        result = r.json()
        
        if "images" in result and len(result["images"]) > 0:
            print(f"✅ Test generation successful!")
            print(f"   Image data length: {len(result['images'][0])} chars")
        else:
            print(f"⚠️  Test generation returned no images")
        
        print(f"\n🎉 A1111 is ready for StAnify!")
        return True
        
    except requests.ConnectionError:
        print(f"❌ Connection failed: A1111 not running at {base_url}")
        print(f"   Start A1111 with: .\\webui-user.bat --api --xformers")
        return False
        
    except requests.HTTPError as e:
        print(f"❌ HTTP error: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Response: {e.response.text}")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    test_a1111_connection()
