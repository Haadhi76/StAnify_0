#!/usr/bin/env python3
"""
Enhanced Stability AI test script with dual-mode support
Tests both engines and images API modes
"""

import sys
import os
import requests
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_stability_modes():
    """Test both Stability API modes."""
    
    print("🚀 DUAL-MODE STABILITY AI TEST")
    print("=" * 50)
    
    api_key = os.getenv("STABILITY_API_KEY", "sk-495lJxbGFmcQEpkQ6UkzrqtQVhxE0wyn59iwYXYUUQKmwl6i")
    base_url = "https://api.stability.ai"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Engines API (current configuration)
    print("🔧 Testing Engines API Mode...")
    print("-" * 30)
    
    engines_payload = {
        "text_prompts": [{"text": "A simple educational tree diagram", "weight": 1.0}],
        "cfg_scale": 7.0,
        "height": 1024,
        "width": 1024,
        "samples": 1,
        "steps": 20,
    }
    
    engines_url = f"{base_url}/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
    print(f"URL: {engines_url}")
    print(f"Payload: {json.dumps(engines_payload, indent=2)}")
    
    try:
        response = requests.post(engines_url, headers=headers, json=engines_payload, timeout=60)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            artifacts = data.get("artifacts", [])
            print(f"✅ SUCCESS: Received {len(artifacts)} artifacts")
            if artifacts:
                print(f"   Artifact keys: {list(artifacts[0].keys())}")
                print(f"   Finish reason: {artifacts[0].get('finishReason', 'unknown')}")
                print(f"   Has base64: {'base64' in artifacts[0]}")
        else:
            print(f"❌ FAILED: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print()
    
    # Test 2: Check what other endpoints are available
    print("🔍 Testing Alternative Endpoints...")
    print("-" * 30)
    
    # Test engines list
    try:
        engines_response = requests.get(f"{base_url}/v1/engines/list", headers=headers)
        if engines_response.status_code == 200:
            engines = engines_response.json()
            print("Available engines:")
            for engine in engines[:3]:  # Show first 3
                print(f"   - {engine['id']}: {engine['name']}")
        else:
            print(f"Engines list failed: {engines_response.status_code}")
    except Exception as e:
        print(f"Engines list error: {e}")
    
    print()
    
    # Test our current implementation
    print("🧪 Testing Current Implementation...")
    print("-" * 30)
    
    try:
        from src.agentic_flow.image_service import ImageService
        from src.agentic_flow.image_panels_contracts import PanelSpec, StyleCard, ReferenceInstruction, SDXLHints
        from src.agentic_flow.settings import settings
        
        print(f"Current mode: {settings.stability_api_mode}")
        print(f"Current model: {settings.stability_model}")
        print(f"txt2img path: {settings.stability_txt2img_path}")
        
        service = ImageService()
        
        # Create test panel
        panel = PanelSpec(
            chunk_id='dual-mode-test',
            caption='Dual mode test',
            positive_prompt='Educational diagram showing a simple math equation: 2 + 2 = 4',
            negative_prompt='blurry, dark, complex',
            reference=ReferenceInstruction(use_previous_image=False),
            style_card=StyleCard(
                render_style='simple illustration',
                palette=['#2E8B57', '#FFD700'],
                camera='top view',
                aspect_ratio='1:1'
            ),
            sdxl_hints=SDXLHints(width=1024, height=1024, steps=20)
        )
        
        print("Generating with current implementation...")
        result_path = service.generate_panel_image(panel, './test_output')
        
        if os.path.exists(result_path):
            size = os.path.getsize(result_path)
            print(f"✅ SUCCESS: Generated {result_path}")
            print(f"📊 File size: {size:,} bytes ({size/1024:.1f} KB)")
            
            if size > 100000:
                print("🎯 RESULT: Real AI-generated image!")
                return True
            else:
                print("📝 RESULT: Placeholder image")
                return False
        else:
            print("❌ ERROR: File not created")
            return False
            
    except Exception as e:
        print(f"❌ Implementation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_smoke_generation():
    """Quick smoke test for image generation."""
    print("\n🔥 SMOKE TEST")
    print("=" * 20)
    
    try:
        from src.agentic_flow.pipeline import run_demo
        
        result = run_demo(
            year="Year 1",
            subject="mathematics", 
            user_prompt="Show 1 + 1 = 2 using simple pictures",
            kb_dir="./kb",
            out_dir="./test_output"
        )
        
        print("Pipeline result:")
        for key, value in result.items():
            if key != "images":  # Don't print long image paths
                print(f"  {key}: {value}")
        
        # Check image sizes
        if 'run_id' in result:
            run_dir = Path("./test_output") / result['run_id']
            if run_dir.exists():
                png_files = list(run_dir.glob("*.png"))
                print(f"\nGenerated {len(png_files)} images:")
                
                for png_file in png_files:
                    size = png_file.stat().st_size
                    status = "🎯 Real AI" if size > 100000 else "📝 Placeholder"
                    print(f"  {png_file.name}: {size:,} bytes - {status}")
                
                return all(png_file.stat().st_size > 100000 for png_file in png_files)
        
        return False
        
    except Exception as e:
        print(f"❌ Smoke test failed: {e}")
        return False

if __name__ == "__main__":
    # Run tests
    implementation_success = test_stability_modes()
    smoke_success = test_smoke_generation()
    
    print("\n" + "="*50)
    print("📋 FINAL RESULTS:")
    print(f"   Implementation Test: {'✅ PASS' if implementation_success else '❌ FAIL'}")
    print(f"   Smoke Test: {'✅ PASS' if smoke_success else '❌ FAIL'}")
    
    if implementation_success and smoke_success:
        print("\n🎉 ALL TESTS PASSED!")
        print("🚀 Stability AI dual-mode integration is working!")
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("🔧 Check configuration and restart Streamlit")
