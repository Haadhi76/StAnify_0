from typing import Literal

from pydantic import BaseModel, confloat, conint, conlist, constr

Caption = constr(strip_whitespace=True, max_length=150)  # Increased from 110 to 150

class CharacterSpec(BaseModel):
    name: str
    age: str | None = None
    clothes: str | None = None
    hair: str | None = None
    notes: str | None = None

class StyleCard(BaseModel):
    render_style: str
    palette: conlist(str, min_items=1)
    camera: str
    aspect_ratio: str
    character_sheet: conlist(CharacterSpec, min_items=0, max_items=6) = []

class ReferenceInstruction(BaseModel):
    use_previous_image: bool
    purpose: Literal["style", "character", "layout"] | None = None
    strength_hint: confloat(ge=0.0, le=1.0) | None = None

class SDXLHints(BaseModel):
    width: conint(ge=256, le=2048) = 1024
    height: conint(ge=256, le=2048) = 768
    cfg_scale: confloat(ge=1.0, le=15.0) = 6.5
    steps: conint(ge=10, le=80) = 30
    sampler: str | None = None
    seed: int | None = None

class PanelSpec(BaseModel):
    chunk_id: str
    caption: Caption
    positive_prompt: str
    negative_prompt: str = ""
    reference: ReferenceInstruction
    continuity_notes: conlist(str, min_items=0, max_items=6) = []
    style_card: StyleCard
    sdxl_hints: SDXLHints = SDXLHints()

class PanelsOutput(BaseModel):
    panels: conlist(PanelSpec, min_items=1)
