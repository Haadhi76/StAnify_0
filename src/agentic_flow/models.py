
from pydantic import BaseModel


class StyleGuidance(BaseModel):
    reading_level: str
    max_steps: int = 5
    numbers_range: tuple[int, int] | None = None
    sentences_max_len: int | None = 14
    vocab_tier_limit: int | None = 1

class Topic(BaseModel):
    id: str
    title: str
    assumed_known: list[str] = []
    allowed_new: list[str] = []
    out_of_scope: list[str] = []
    vocab_known: list[str] = []
    vocab_avoid: list[str] = []
    representations_allowed: list[str] = []
    typical_misconceptions: list[str] = []
    style_guidance: StyleGuidance

class Subject(BaseModel):
    name: str
    topics: list[Topic]

class YearKB(BaseModel):
    year: str
    key_stage: str
    subjects: dict[str, Subject]

class CurriculumKB(BaseModel):
    years: dict[str, YearKB]
