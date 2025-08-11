
from pydantic import BaseModel, conint, conlist, constr

ChunkID = constr(strip_whitespace=True, min_length=1, max_length=64)

class ChunkSpec(BaseModel):
    chunk_id: ChunkID
    index: conint(ge=0)
    title: constr(strip_whitespace=True, max_length=120)  # Increased from 80 to 120
    text: constr(strip_whitespace=True, max_length=600)
    goal: constr(strip_whitespace=True, max_length=160)
    setting: constr(max_length=80) | None = None
    characters: conlist(str, min_items=0, max_items=5) = []
    actions: conlist(str, min_items=0, max_items=6) = []
    props: conlist(str, min_items=0, max_items=8) = []
    visual_tags: conlist(str, min_items=0, max_items=10) = []
    constraints_notes: conlist(str, min_items=0, max_items=6) = []

class ChunksOutput(BaseModel):
    narrative: constr(strip_whitespace=True, min_length=1)
    chunks: conlist(ChunkSpec, min_items=1)
