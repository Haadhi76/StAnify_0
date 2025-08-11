from reportlab.platypus import SimpleDocTemplate, Image, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from PIL import Image as PILImage
from pathlib import Path

img_path = Path("exports").rglob("panel_c1.png")
img_path = next(img_path, None)
assert img_path and img_path.exists(), f"No panel image found in exports"

print(f"Found image: {img_path}")
print(f"Image size: {img_path.stat().st_size} bytes")

# normalize to PNG RGB on disk
norm = img_path.with_name(img_path.stem + "_norm.png")
with PILImage.open(img_path) as im:
    print(f"Original mode: {im.mode}, size: {im.size}")
    if im.mode not in ("RGB", "L", "P"):
        im = im.convert("RGB")
    im.save(norm, format="PNG")

print(f"Normalized to: {norm}")
print(f"Normalized size: {norm.stat().st_size} bytes")

doc = SimpleDocTemplate("tools/_embed_test.pdf", pagesize=A4)
styles = getSampleStyleSheet()
flow = [Paragraph("Embed Test", styles["Title"]), Spacer(1, 12)]
flow.append(Image(str(norm), width=400, height=300))
doc.build(flow)
print("✅ Wrote tools/_embed_test.pdf")
