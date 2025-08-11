"""
Chunk Maker Agent: Converts educational content into structured learning chunks.
"""

import json
import logging
from pathlib import Path
from typing import List

from .chunks_contracts import ChunkSpec, ChunksOutput
from .llm_client import llm_client
from .refined_prompt_contracts import RefinedPromptSpec

logger = logging.getLogger(__name__)

# Load templates
TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
CHUNK_SYSTEM_TEMPLATE = (TEMPLATES_DIR / "chunk_system.txt").read_text(encoding="utf-8")
CHUNK_USER_TEMPLATE = (TEMPLATES_DIR / "chunk_user.txt").read_text(encoding="utf-8")


def generate_chunks_from_content(
    year: str,
    subject: str, 
    topic: str,
    refined: RefinedPromptSpec,
    narrative_context: str
) -> List[ChunkSpec]:
    """
    Generate educational content chunks using LLM agent.
    
    Args:
        year: Target year/grade level
        subject: Subject area
        topic: Specific topic being taught
        refined: Refined prompt specification
        narrative_context: Educational narrative context
        
    Returns:
        List of chunk specifications
        
    Raises:
        RuntimeError: If chunk generation fails or produces invalid JSON
    """
    
    # Prepare context for the LLM
    user_prompt = CHUNK_USER_TEMPLATE.format(
        year=year,
        subject=subject,
        topic=topic,
        narrative_brief=refined.narrative_brief.json() if hasattr(refined.narrative_brief, 'json') else str(refined.narrative_brief),
        refined_prompt_text=refined.notes_for_writers,  # Fixed attribute name
        style_context=f"Style: {refined.style_card.render_style}, Setting: {refined.narrative_brief.setting}",
        learning_objective="; ".join(refined.learning_objectives)  # Fixed: use plural and join list
    )
    
    try:
        # Generate chunks using LLM
        raw_response = llm_client.generate_json(
            model="gpt-4o",  # Fixed parameter name
            system_prompt=CHUNK_SYSTEM_TEMPLATE,
            user_prompt=user_prompt,
            schema_name="ChunksOutput",
            max_tokens=1500,
            temperature=0.7
        )
        
        logger.info(f"Chunk Maker raw response: {json.dumps(raw_response, indent=2)}")
        
        # Validate JSON structure
        try:
            chunks_output = ChunksOutput.parse_obj(raw_response)
        except Exception as e:
            logger.error("Chunks JSON invalid: %s\nRAW=%s", e, raw_response)
            raise RuntimeError("Chunk Maker produced invalid JSON") from e
        
        # Validate we got chunks
        if not chunks_output.chunks:
            logger.error("No chunks produced by Chunk Maker")
            raise RuntimeError("No chunks produced by Chunk Maker")
        
        # Validate chunk count is reasonable (2-4 chunks)
        if not (2 <= len(chunks_output.chunks) <= 4):
            logger.warning(f"Unusual chunk count: {len(chunks_output.chunks)} (expected 2-4)")
        
        logger.info(f"Generated {len(chunks_output.chunks)} chunks successfully")
        return chunks_output.chunks
        
    except Exception as e:
        logger.error(f"Chunk generation failed: {e}")
        
        # Fallback to enhanced default chunks with proper context
        logger.info("Using fallback chunk generation with context")
        return _create_fallback_chunks(refined, narrative_context, topic)


def _create_fallback_chunks(refined: RefinedPromptSpec, narrative_context: str, topic: str) -> List[ChunkSpec]:
    """Create contextual fallback chunks when LLM generation fails."""
    
    # Extract key elements from refined prompt
    setting = getattr(refined.narrative_brief, 'setting', 'classroom')
    characters = getattr(refined.narrative_brief, 'characters', ['student'])
    must_include = getattr(refined.narrative_brief, 'must_include', [])
    
    chunks = [
        ChunkSpec(
            chunk_id="c1", 
            index=0, 
            title=f"Introduce {topic}",
            text=f"Meet our characters in the {setting}. {narrative_context[:100]}...",
            goal="Establish the learning context and introduce the problem",
            setting=setting,
            characters=characters,
            actions=["introduce problem", "show initial situation", "set context"],
            props=["learning materials"] + must_include,
            visual_tags=refined.visual_tags[:3] if refined.visual_tags else ["educational", "child-friendly", "clear"]
        ),
        ChunkSpec(
            chunk_id="c2", 
            index=1, 
            title=f"Explore {topic}",
            text=f"Work through the {topic} step by step with our characters.",
            goal="Demonstrate the solution process and key learning points",
            setting=setting,
            characters=characters,
            actions=["apply method", "show solution", "demonstrate learning"],
            props=["solution tools", "educational aids"] + must_include,
            visual_tags=refined.visual_tags[:5] if refined.visual_tags else ["problem-solving", "step-by-step", "engaging"]
        )
    ]
    
    return chunks
