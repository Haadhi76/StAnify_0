from datetime import datetime
from typing import Literal

from pydantic import BaseModel, conlist, constr

from .critique_contracts import CritiqueScores
from .refined_prompt_contracts import RefinedPromptSpec
from .refined_prompt_contracts import StyleCard as RefStyleCard

Verdict = Literal["Pass", "Soft Pass", "Fail"]
RunID = constr(strip_whitespace=True, min_length=6, max_length=64)

class TaskMeta(BaseModel):
    run_id: RunID
    user_id: str | None = None
    year: str
    subject: str
    topic_id: str
    created_at: datetime
    model_notes: str | None = None

class PanelProvenance(BaseModel):
    prompt_text: str
    negative_prompt: str = ""
    sdxl_width: int
    sdxl_height: int
    cfg_scale: float
    steps: int
    sampler: str | None = None
    seed: int | None = None
    used_previous_image: bool
    reference_purpose: str | None = None
    reference_strength_hint: float | None = None
    iterations: int = 1

class PanelCritiqueSummary(BaseModel):
    verdict: Verdict
    scores: CritiqueScores
    evidence: list[str] = []
    notes: str | None = None

class ManifestPanel(BaseModel):
    chunk_id: str
    index: int
    caption: str
    image_uri: str
    style_card: RefStyleCard
    provenance: PanelProvenance
    critique: PanelCritiqueSummary | None = None

class OverallCritique(BaseModel):
    verdict: Verdict
    scores: CritiqueScores
    evidence: list[str] = []
    feedback_for_analogy: str
    feedback_for_narrative: str

class RunManifest(BaseModel):
    version: str = "1.0.0"
    task: TaskMeta
    refined_prompt: RefinedPromptSpec
    narrative: str
    chunks: list[dict]
    panels: conlist(ManifestPanel, min_items=1)
    overall_critique: OverallCritique
    final_verdict: Verdict
    summary_notes: str | None = None
