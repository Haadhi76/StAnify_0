from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..chunks_contracts import ChunkSpec
from ..manifest_contracts import RunManifest


def _overall_score(scores):
    """
    Calculate overall score from CritiqueScores (works with dict or Pydantic model).
    
    Args:
        scores: CritiqueScores model or dict
        
    Returns:
        float: Overall score or None if cannot calculate
    """
    if not scores:
        return None
    
    # if it's a dict already
    if isinstance(scores, dict):
        if "overall_score" in scores:
            return scores["overall_score"]
        keys = ("alignment", "vocab", "scope", "cognitive_load")
        vals = [scores.get(k) for k in keys if k in scores and isinstance(scores.get(k), (int, float))]
        return round(sum(vals) / len(vals), 2) if vals else None
    
    # otherwise assume Pydantic model (v1)
    try:
        a = getattr(scores, "alignment", None)
        v = getattr(scores, "vocab", None)
        s = getattr(scores, "scope", None)
        c = getattr(scores, "cognitive_load", None)
        vals = [x for x in (a, v, s, c) if isinstance(x, (int, float))]
        return round(sum(vals) / len(vals), 2) if vals else None
    except Exception:
        return None


def _fetch_image(uri: str) -> BytesIO:
    if not uri:
        raise FileNotFoundError("Empty image URI")

    # file:// support (Windows & *nix)
    if uri.startswith("file://"):
        parsed = urlparse(uri)
        p = Path(unquote(parsed.path))
        if parsed.netloc:  # windows drive in netloc (rare), join it
            p = Path(f"{parsed.netloc}{p.as_posix()}")
        with open(p, "rb") as f:
            data = f.read()
        bio = BytesIO(data); bio.seek(0); return bio

    # http(s)
    if uri.startswith("http://") or uri.startswith("https://"):
        r = requests.get(uri, timeout=30)
        r.raise_for_status()
        bio = BytesIO(r.content); bio.seek(0); return bio

    # plain local path
    with open(Path(uri), "rb") as f:
        data = f.read()
    bio = BytesIO(data); bio.seek(0); return bio

def _image_size(bio: BytesIO):
    bio.seek(0)
    with PILImage.open(bio) as im:
        return im.width, im.height

def _as_png_rgb(bio: BytesIO) -> BytesIO:
    """Convert image to PNG RGB format for ReportLab compatibility."""
    bio.seek(0)
    with PILImage.open(bio) as im:
        if im.mode not in ("RGB", "L", "P"):
            im = im.convert("RGB")
        out = BytesIO()
        im.save(out, format="PNG")
        out.seek(0)
        return out

def export_manifest_to_pdf(manifest: RunManifest, out_path: str) -> str:
    page_size = landscape(A4)
    doc = SimpleDocTemplate(out_path, pagesize=page_size, leftMargin=1.2*cm, rightMargin=1.2*cm, topMargin=1.0*cm, bottomMargin=1.0*cm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Caption", parent=styles["BodyText"], leading=14, spaceBefore=8, spaceAfter=6))
    styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontSize=28, spaceAfter=20, alignment=1))
    styles.add(ParagraphStyle(name="CoverSubtitle", parent=styles["Heading2"], fontSize=18, spaceAfter=15, alignment=1))
    styles.add(ParagraphStyle(name="Objective", parent=styles["BodyText"], leftIndent=20, spaceBefore=6))

    flow = []
    
    # === COVER PAGE ===
    flow.append(Spacer(1, 2*cm))
    flow.append(Paragraph("🎓 StAnify Educational Content", styles["CoverTitle"]))
    flow.append(Paragraph(f"{manifest.task.year} {manifest.task.subject.title()}", styles["CoverSubtitle"]))
    flow.append(Paragraph(f"Topic: {manifest.refined_prompt.topic_title}", styles["CoverSubtitle"]))
    
    # Learning objectives
    flow.append(Spacer(1, 1*cm))
    flow.append(Paragraph("📋 Learning Objectives:", styles["Heading2"]))
    
    # Extract objectives from refined prompt or create generic ones
    objectives = getattr(manifest.refined_prompt, 'learning_objectives', None)
    if not objectives:
        # Generate default objectives based on topic
        objectives = [
            f"Understand the concept of {manifest.refined_prompt.topic_title.lower()}",
            "Apply learning through visual examples and practical activities",
            "Demonstrate understanding through guided practice"
        ]
    
    for obj in objectives:
        flow.append(Paragraph(f"• {obj}", styles["Objective"]))
    
    # Metadata table
    flow.append(Spacer(1, 1*cm))
    
    # Calculate overall score using robust helper
    overall = _overall_score(getattr(manifest.overall_critique, "scores", None))
    
    meta_tbl = [
        ["Run ID", manifest.task.run_id],
        ["Generated", manifest.task.created_at.isoformat()],
        ["Content Panels", str(len(manifest.panels))],
        ["Quality Score", f"{overall if overall is not None else 'N/A'}"]
    ]
    tbl = Table(meta_tbl, hAlign="CENTER")
    tbl.setStyle(TableStyle([
        ("BOX",(0,0),(-1,-1),0.25,colors.grey),
        ("INNERGRID",(0,0),(-1,-1),0.25,colors.grey),
        ("BACKGROUND",(0,0),(0,-1),colors.lightgrey)
    ]))
    flow.append(tbl)
    flow.append(PageBreak())
    
    # === CONTENT PAGES ===
    chunk_by_id = {c.chunk_id: c for c in [ChunkSpec(**cc) if isinstance(cc, dict) else cc for cc in manifest.chunks]}

    max_w = page_size[0] - 2.4*cm
    max_h = page_size[1] - 5.0*cm
    for i, panel in enumerate(sorted(manifest.panels, key=lambda p: p.index)):
        chunk = chunk_by_id.get(panel.chunk_id)
        title = f"Panel {panel.index + 1}: {chunk.title if chunk else panel.chunk_id}"
        flow.append(Paragraph(title, styles["Heading2"]))
        try:
            bio = _fetch_image(panel.image_uri)
            bio = _as_png_rgb(bio)  # normalize to PNG RGB
            iw, ih = _image_size(bio)
            scale = min(max_w/iw, max_h/ih, 1.0)
            flow.append(Image(bio, width=iw*scale, height=ih*scale))
        except Exception:
            flow.append(Paragraph("[Image unavailable]", styles["BodyText"]))
        
        flow.append(Paragraph(panel.caption or "", styles["Caption"]))
        
        # Add chunk body text under the caption
        if panel.chunk_id in chunk_by_id:
            ch = chunk_by_id[panel.chunk_id]
            flow.append(Paragraph(ch.text, styles["BodyText"]))
        
        if i < len(manifest.panels) - 1:
            flow.append(PageBreak())
    
    # === CLOSING PAGE ===
    flow.append(PageBreak())
    flow.append(Spacer(1, 1*cm))
    flow.append(Paragraph("✅ Success Criteria & Assessment", styles["Heading1"]))
    
    # Success criteria
    flow.append(Spacer(1, 0.5*cm))
    flow.append(Paragraph("🎯 Success Criteria:", styles["Heading2"]))
    
    success_criteria = [
        f"Can explain key concepts from {manifest.refined_prompt.topic_title.lower()}",
        "Demonstrates understanding through examples and activities",
        "Shows confidence in applying new knowledge",
        "Can connect learning to real-world situations"
    ]
    
    for criteria in success_criteria:
        flow.append(Paragraph(f"✓ {criteria}", styles["Objective"]))
    
    # Overall critique and feedback
    if manifest.overall_critique:
        flow.append(Spacer(1, 1*cm))
        flow.append(Paragraph("📊 Content Quality Assessment", styles["Heading2"]))
        
        critique = manifest.overall_critique
        verdict_map = {"Pass": "🟢", "Soft Pass": "🟡", "Fail": "🔴"}
        verdict_emoji = verdict_map.get(critique.verdict, "🔴")
        
        flow.append(Paragraph(f"Overall Verdict: {verdict_emoji} {critique.verdict}", styles["BodyText"]))
        
        if hasattr(critique, 'scores') and critique.scores:
            scores = critique.scores
            score_text = f"Alignment: {getattr(scores, 'alignment', 'N/A')} | "
            score_text += f"Vocabulary: {getattr(scores, 'vocab', 'N/A')} | "
            score_text += f"Scope: {getattr(scores, 'scope', 'N/A')} | "
            score_text += f"Cognitive Load: {getattr(scores, 'cognitive_load', 'N/A')}"
            flow.append(Paragraph(score_text, styles["BodyText"]))
        
        if critique.evidence:
            flow.append(Paragraph("Key Feedback:", styles["Heading3"]))
            for evidence in critique.evidence[:3]:  # Top 3 feedback points
                flow.append(Paragraph(f"• {evidence}", styles["Objective"]))
    
    # Generation info
    flow.append(Spacer(1, 1*cm))
    flow.append(Paragraph("🤖 Generated by StAnify AI", styles["Caption"]))
    flow.append(Paragraph(f"Educational content platform with image continuity evaluation", styles["Caption"]))

    doc.build(flow)
    return out_path
