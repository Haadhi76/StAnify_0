# tools/inspect_manifest.py
import json, sys
from pathlib import Path
from PIL import Image

def inspect(manifest_path: Path):
    m = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    panels = m.get("panels", [])
    print(f"Manifest: {manifest_path}")
    print(f"Panels: {len(panels)}")
    for i, p in enumerate(panels):
        uri = p.get("image_uri", "")
        path = Path(uri)
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        print(f"[{i+1}] chunk={p.get('chunk_id')} uri={uri}")
        print(f"     exists={exists} size={size}")
        if exists:
            try:
                im = Image.open(path)
                im.verify()  # validate file integrity
                print("     PIL.verify() = OK")
            except Exception as e:
                print("     PIL.verify() FAIL:", e)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # auto-pick newest manifest from exports
        exports = Path("exports")
        candidates = sorted(exports.glob("**/*.manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            print("No manifests found in ./exports")
            sys.exit(1)
        inspect(candidates[0])
    else:
        inspect(Path(sys.argv[1]))
