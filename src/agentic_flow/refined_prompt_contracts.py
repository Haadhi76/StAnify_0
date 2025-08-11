from pydantic import BaseModel, conlist, constr

AspectRatio = constr(regex=r"^\d+:\d+$")

class StyleCard(BaseModel):
    render_style: str
    palette: conlist(str, min_items=1)
    camera: str
    aspect_ratio: AspectRatio
    character_consistency: str

class Constraints(BaseModel):
    reading_level: str
    max_steps: int
    numbers_range: tuple[int, int] | None = None
    representations_allowed: conlist(str, min_items=0) = []
    vocab_prefer: conlist(str, min_items=0) = []
    vocab_avoid: conlist(str, min_items=0) = []
    out_of_scope: conlist(str, min_items=0) = []

class Pedagogy(BaseModel):
    activate_prior_knowledge: str
    address_misconceptions: conlist(str, min_items=0, max_items=3) = []
    tone_style: str

class NarrativeBrief(BaseModel):
    setting: str
    characters: conlist(str, min_items=0, max_items=2) = []
    must_include: conlist(str, min_items=0, max_items=4) = []
    must_avoid: conlist(str, min_items=0, max_items=4) = []

class RefinedPromptSpec(BaseModel):
    year: str
    subject: str
    topic_id: str
    topic_title: str
    learning_objectives: conlist(str, min_items=1, max_items=3)
    success_criteria: conlist(str, min_items=1, max_items=3)
    constraints: Constraints
    pedagogy: Pedagogy
    narrative_brief: NarrativeBrief
    visual_tags: conlist(str, min_items=0, max_items=8) = []
    style_card: StyleCard
    notes_for_writers: str
