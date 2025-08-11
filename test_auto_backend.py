#!/usr/bin/env python3
"""
Test script for the enhanced auto backend selection system.
Demonstrates the new dynamic backend switching and circuit breaker functionality.
"""

from src.agentic_flow.image_service import image_service
from src.agentic_flow.image_panels_contracts import PanelSpec, SDXLHints, StyleCard, ReferenceInstruction
import time
import os

def test_auto_backend_system():
    """Test the enhanced auto backend system."""
    
    print("🎉 ENHANCED STANIFY AUTO-BACKEND SYSTEM TEST")
    print("=" * 50)
    print()
    
    # Show current configuration
    print("🔧 BACKEND CONFIGURATION:")
    print(f"   Configured: {image_service.backend}")
    print(f"   Active: {image_service._active_backend}")
    print()
    
    # Show detailed status
    print("📊 SYSTEM STATUS:")
    status = image_service.get_status()
    for key, value in status.items():
        if key == 'cb_open_until' and value > 0:
            remaining = max(0, value - time.time())
            print(f"   {key}: {value} (closes in {remaining:.1f}s)")
        else:
            print(f"   {key}: {value}")
    print()
    
    # Test image generation
    print("🎨 GENERATING TEST IMAGE:")
    
    style_card = StyleCard(
        render_style='educational illustration',
        palette=['blue', 'green', 'orange'],
        camera='wide angle',
        aspect_ratio='16:9'
    )
    
    reference = ReferenceInstruction(use_previous_image=False)
    
    panel = PanelSpec(
        chunk_id='auto_test',
        caption='Testing enhanced auto backend',
        positive_prompt='colorful educational illustration of children learning mathematics',
        negative_prompt='blurry, dark',
        reference=reference,
        style_card=style_card,
        sdxl_hints=SDXLHints(width=1024, height=768)
    )
    
    # Generate image and show result
    result = image_service.generate_panel_image(panel, 'exports/')
    print(f"✅ Generated: {result}")
    
    if result and os.path.exists(result):
        size = os.path.getsize(result)
        print(f"📁 File size: {size} bytes")
        print(f"🎯 Backend used: {image_service._active_backend}")
    else:
        print("❌ File not found")
    
    print()
    
    # Explain behavior
    print("🔄 SYSTEM BEHAVIOR:")
    if image_service.backend == "auto":
        if status['a1111_ok']:
            print("   ✅ AUTO mode: A1111 available → using sdxl-a1111")
            print("   🎨 Real AI image generation active!")
        else:
            cb_active = status['cb_open_until'] > time.time()
            if cb_active:
                print("   🔴 AUTO mode: Circuit breaker OPEN → using placeholder")
                print("   ⏳ Waiting for circuit breaker to reset before retrying A1111")
            else:
                print("   🟡 AUTO mode: A1111 offline → using placeholder")
                print("   🔧 When A1111 starts, system will auto-switch to real AI generation")
            print("   📋 Enhanced placeholders with visible labels active")
    else:
        print(f"   📌 MANUAL mode: explicitly using {image_service.backend}")
    
    print()
    print("💡 TO TEST AUTO-SWITCHING:")
    print("   1. Start A1111: cd stable-diffusion-webui && .\\webui-user.bat --api --xformers")
    print("   2. Wait for: 'Running on local URL: http://127.0.0.1:7860'")
    print("   3. Run this test again → should auto-switch to 'sdxl-a1111'")
    print("   4. Stop A1111 → should auto-switch back to 'placeholder'")

if __name__ == "__main__":
    test_auto_backend_system()
