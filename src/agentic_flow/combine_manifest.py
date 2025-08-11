from datetime import datetime

from .chunks_contracts import ChunkSpec
from .critique_contracts import CritiqueOutput
from .image_panels_contracts import PanelsOutput
from .manifest_contracts import (
    ManifestPanel,
    OverallCritique,
    PanelCritiqueSummary,
    PanelProvenance,
    RunManifest,
    TaskMeta,
)
from .refined_prompt_contracts import RefinedPromptSpec


def build_manifest(
    run_id: str,
    user_id: str | None,
    year: str,
    subject: str,
    refined: RefinedPromptSpec,
    narrative: str,
    chunks: list[ChunkSpec],
    panels_out: PanelsOutput,
    image_uris_by_chunk: dict[str, str],
    panel_critiques_by_chunk: dict[str, CritiqueOutput],
    overall_critique: CritiqueOutput,
    model_notes: str | None = None,
) -> RunManifest:
    task = TaskMeta(
        run_id=run_id, user_id=user_id, year=year, subject=subject,
        topic_id=refined.topic_id, created_at=datetime.utcnow(), model_notes=model_notes
    )
    chunk_idx = {c.chunk_id: c.index for c in chunks}
    manifest_panels = []
    for p in panels_out.panels:
        img_uri = image_uris_by_chunk.get(p.chunk_id, "")
        pc = panel_critiques_by_chunk.get(p.chunk_id)
        prov = PanelProvenance(
            prompt_text=p.positive_prompt,
            negative_prompt=p.negative_prompt,
            sdxl_width=p.sdxl_hints.width,
            sdxl_height=p.sdxl_hints.height,
            cfg_scale=p.sdxl_hints.cfg_scale,
            steps=p.sdxl_hints.steps,
            sampler=p.sdxl_hints.sampler,
            seed=p.sdxl_hints.seed,
            used_previous_image=p.reference.use_previous_image,
            reference_purpose=p.reference.purpose,
            reference_strength_hint=p.reference.strength_hint,
            iterations=1,
        )
        crit_summary = None
        if pc:
            crit_summary = PanelCritiqueSummary(
                verdict=pc.verdict, scores=pc.scores, evidence=pc.evidence,
                notes="; ".join(pc.evidence[:2]) if pc.evidence else None
            )
        manifest_panels.append(
            ManifestPanel(
                chunk_id=p.chunk_id, index=chunk_idx.get(p.chunk_id, 0),
                caption=p.caption, image_uri=img_uri, style_card=refined.style_card,
                provenance=prov, critique=crit_summary
            )
        )

    overall = OverallCritique(
        verdict=overall_critique.verdict, scores=overall_critique.scores,
        evidence=overall_critique.evidence,
        feedback_for_analogy=overall_critique.feedback_for_analogy,
        feedback_for_narrative=overall_critique.feedback_for_narrative
    )

    panel_verdicts = [p.critique.verdict for p in manifest_panels if p.critique]
    if "Fail" in panel_verdicts or overall.verdict == "Fail":
        final_verdict = "Fail"
    elif "Soft Pass" in panel_verdicts or overall.verdict == "Soft Pass":
        final_verdict = "Soft Pass"
    else:
        final_verdict = "Pass"

    return RunManifest(
        task=task, refined_prompt=refined, narrative=narrative,
    chunks=[c.dict() for c in chunks], panels=manifest_panels,
        overall_critique=overall, final_verdict=final_verdict,
        summary_notes="Hello-world run."
    )
