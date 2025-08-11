#!/usr/bin/env python3
"""Test script to verify the Stability AI fix is working"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.agentic_flow.image_service import ImageService
from src.agentic_flow.image_panels_contracts import PanelSpec, StyleCard, ReferenceInstruction, SDXLHints

def test_stability_fix():
    print("🔧 TESTING STABILITY AI FIX")
    print("=" * 40)
    
    service = ImageService()
    print(f"Active backend: {service._active_backend}")
    
    # Create test panel
    panel = PanelSpec(
        chunk_id='fix-verification',
        caption='Fix verification test',
        positive_prompt='Educational diagram showing 2 red apples plus 1 green apple equals 3 apples total, simple illustration for children',
        negative_prompt='blurry, dark, complex, realistic',
        reference=ReferenceInstruction(use_previous_image=False),
        style_card=StyleCard(
            render_style='simple illustration',
            palette=['#FF0000', '#00FF00'],
            camera='top view',
            aspect_ratio='1:1'
        ),
        sdxl_hints=SDXLHints(width=1024, height=1024, steps=25)
    )
    
    print(f"Testing with prompt: {panel.positive_prompt[:60]}...")
    
    try:
        result_path = service.generate_panel_image(panel, './test_output')
        
        if os.path.exists(result_path):
            size = os.path.getsize(result_path)
            print(f"✅ SUCCESS: Generated {result_path}")
            print(f"📊 File size: {size:,} bytes ({size/1024:.1f} KB)")
            
            if size > 100000:  # > 100KB
                print("🎯 RESULT: Real AI-generated image!")
                return True
            else:
                print("📝 RESULT: Placeholder image (fix not working)")
                return False
        else:
            print("❌ ERROR: File not found")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_stability_fix()
    print("\n" + "="*40)
    if success:
        print("🎉 FIX WORKING: Stability AI generates real images!")
    else:
        print("⚠️  FIX NOT WORKING: Still generating placeholder images")
