# test_a1111_connection.py
import os, base64, json
from pathlib import Path
import requests

BASE = os.getenv("A1111_BASE_URL", "http://127.0.0.1:7860")
MODEL = os.getenv("A1111_MODEL", "sdxl_base_1.0")

def b64_to_file(b64, path: Path):
    if "," in b64:
        b64 = b64.split(",", 1)[1]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(b64))

try:
    print(f"� Testing A1111 at {BASE}")
    print(f"🎯 Looking for model: {MODEL}")
    print("-" * 60)
    
    # 1) Healthcheck: list models and confirm your checkpoint name
    print("1. Fetching available models...")
    r = requests.get(f"{BASE}/sdapi/v1/sd-models", timeout=15)
    r.raise_for_status()
    models = [m.get("model_name") or m.get("title") for m in r.json()]
    print("Found models:", models[:5], "..." if len(models) > 5 else "")
    
    # Check if our model is available
    model_found = any(MODEL in (m or "") for m in models)
    if not model_found:
        print(f"❌ Model '{MODEL}' not found.")
        print("Available models:", models)
        print("Update A1111_MODEL to match an exact name from above.")
        exit(1)
    
    print(f"✅ Model '{MODEL}' found!")
    
    # 2) Set the checkpoint explicitly (optional but reduces surprises)
    print("2. Setting model checkpoint...")
    payload_opts = {"sd_model_checkpoint": MODEL}
    r = requests.post(f"{BASE}/sdapi/v1/options", json=payload_opts, timeout=30)
    r.raise_for_status()
    print(f"✅ Set model: {MODEL}")
    
    # 3) Quick txt2img smoke (small image for speed)
    print("3. Generating smoke test image...")
    payload = {
        "prompt": "cute classroom illustration, child-friendly, colorful, simple shapes, educational scene",
        "negative_prompt": "text, watermark, logo, gore, weapons, nsfw, low quality",
        "width": 512, "height": 384,
        "steps": 20, "cfg_scale": 6.5,
        "sampler_name": "Euler a",   # very compatible; swap to your preferred sampler later
        "seed": -1, "batch_size": 1, "n_iter": 1,
    }
    r = requests.post(f"{BASE}/sdapi/v1/txt2img", json=payload, timeout=120)
    r.raise_for_status()
    out = Path("exports/_smoke_a1111.png")
    b64_to_file(r.json()["images"][0], out)
    
    print(f"✅ Generated image: {out.resolve()}")
    print(f"📏 File size: {out.stat().st_size} bytes")
    print()
    print("🎉 A1111 is working perfectly!")
    print("✅ Your StAnify runs will now generate real AI images!")
    
except requests.ConnectionError:
    print(f"❌ Connection failed: A1111 not running at {BASE}")
    print("Start A1111 with: .\\webui-user.bat --api --xformers")
except requests.HTTPError as e:
    print(f"❌ HTTP error: {e}")
    if hasattr(e, 'response') and e.response:
        print(f"Response: {e.response.text}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
