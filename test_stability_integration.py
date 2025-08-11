#!/usr/bin/env python3
"""
Comprehensive test for StAnify Stability AI backend integration.
Tests the full StAnify pipeline with Stability AI image generation.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agentic_flow.image_service import image_service
from src.agentic_flow.image_panels_contracts import PanelSpec, SDXLHints, StyleCard, ReferenceInstruction

def test_stability_integration():
    """Test complete StAnify integration with Stability AI backend."""
    
    print("🎨 STANIFY STABILITY AI INTEGRATION TEST")
    print("=" * 50)
    
    # Check environment setup
    api_key = os.getenv("STABILITY_API_KEY")
    backend = os.getenv("IMAGE_BACKEND", image_service.backend)
    
    print("🔧 CONFIGURATION:")
    print(f"   IMAGE_BACKEND: {backend}")
    print(f"   Stability API Key: {'✅ Set' if api_key else '❌ Missing'}")
    print(f"   Active backend: {image_service._active_backend}")
    
    if not api_key:
        print("\n❌ Error: STABILITY_API_KEY not set")
        print("   Set it with: export STABILITY_API_KEY=sk-...")
        return False
    
    print()
    
    # Show detailed backend status
    print("📊 BACKEND STATUS:")
    status = image_service.get_status()
    for key, value in status.items():
        print(f"   {key}: {value}")
    print()
    
    # Test 1: txt2img generation
    print("🧪 TEST 1: txt2img Generation")
    print("-" * 30)
    
    style_card = StyleCard(
        render_style='educational illustration',
        palette=['blue', 'green', 'orange', 'yellow'],
        camera='wide angle',
        aspect_ratio='16:9'
    )
    
    reference = ReferenceInstruction(use_previous_image=False)
    
    panel1 = PanelSpec(
        chunk_id='stability_test_01',
        caption='Testing Stability AI txt2img generation',
        positive_prompt='A bright, colorful educational illustration showing children learning basic math with numbers 1 to 10, cartoon style, friendly characters',
        negative_prompt='dark, scary, violent, text overlay, watermark',
        reference=reference,
        style_card=style_card,
        sdxl_hints=SDXLHints(width=1024, height=768, steps=25, cfg_scale=7.0)
    )
    
    try:
        result1 = image_service.generate_panel_image(panel1, 'exports/')
        if result1 and Path(result1).exists():
            size1 = Path(result1).stat().st_size
            print(f"✅ txt2img Success: {result1}")
            print(f"   📏 File size: {size1:,} bytes")
            print(f"   🎯 Backend used: {image_service._active_backend}")
        else:
            print(f"❌ txt2img Failed: No file generated")
            return False
    except Exception as e:
        print(f"❌ txt2img Error: {e}")
        return False
    
    print()
    
    # Test 2: img2img continuity generation
    print("🧪 TEST 2: img2img Continuity Generation")
    print("-" * 40)
    
    reference2 = ReferenceInstruction(
        use_previous_image=True,
        purpose="style",
        strength_hint=0.7
    )
    
    panel2 = PanelSpec(
        chunk_id='stability_test_02',
        caption='Testing Stability AI img2img with continuity',
        positive_prompt='The same educational scene but now showing children counting apples and oranges, maintaining the same style and characters',
        negative_prompt='dark, scary, violent, text overlay, watermark',
        reference=reference2,
        style_card=style_card,
        sdxl_hints=SDXLHints(width=1024, height=768, steps=25, cfg_scale=7.0)
    )
    
    try:
        result2 = image_service.generate_panel_image(panel2, 'exports/', reference_image_path=result1)
        if result2 and Path(result2).exists():
            size2 = Path(result2).stat().st_size
            print(f"✅ img2img Success: {result2}")
            print(f"   📏 File size: {size2:,} bytes")
            print(f"   🎯 Backend used: {image_service._active_backend}")
            print(f"   🔗 Reference: {Path(result1).name}")
        else:
            print(f"❌ img2img Failed: No file generated")
            return False
    except Exception as e:
        print(f"❌ img2img Error: {e}")
        return False
    
    print()
    
    # Verify both images are different (not placeholders)
    print("🔍 VERIFICATION:")
    if size1 > 50000 and size2 > 50000:  # Real AI images are typically >50KB
        print("✅ Both images appear to be real AI-generated content")
        print(f"   📊 Size difference: {abs(size2 - size1):,} bytes")
    else:
        print("⚠️  Warning: Small file sizes suggest placeholder fallback")
    
    # Check if files are actually different
    if Path(result1).read_bytes() != Path(result2).read_bytes():
        print("✅ Images are unique (not identical)")
    else:
        print("⚠️  Warning: Images appear identical")
    
    print()
    print("🎉 STABILITY AI INTEGRATION TEST COMPLETE!")
    print(f"✅ Generated files: {Path(result1).name}, {Path(result2).name}")
    print("📁 Check exports/ directory for results")
    
    return True

if __name__ == "__main__":
    success = test_stability_integration()
    exit(0 if success else 1)
