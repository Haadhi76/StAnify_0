"""
Image Prompter Agent: Converts chunks into detailed panel specifications for image generation.
"""

import json
import logging
from pathlib import Path
from typing import List

from .chunks_contracts import ChunkSpec
from .image_panels_contracts import (
    CharacterSpec,
    PanelsOutput,
    PanelSpec,
    ReferenceInstruction,
    SDXLHints,
    StyleCard as PanelStyleCard
)
from .llm_client import llm_client
from .refined_prompt_contracts import RefinedPromptSpec
from .settings import settings

logger = logging.getLogger(__name__)

# Load templates
TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
IMAGE_PROMPTER_SYSTEM = (TEMPLATES_DIR / "image_prompter_system.txt").read_text(encoding="utf-8")
IMAGE_PROMPTER_USER = (TEMPLATES_DIR / "image_prompter_user.txt").read_text(encoding="utf-8")


def generate_panels_from_chunks(chunks: List[ChunkSpec], refined: RefinedPromptSpec) -> PanelsOutput:
    """
    Generate panel specifications from chunks using LLM agent.
    
    Args:
        chunks: List of chunk specifications to convert to panels
        refined: Refined prompt specification for style and context
        
    Returns:
        PanelsOutput with panel specifications
        
    Raises:
        RuntimeError: If panel generation fails or produces invalid JSON
    """
    
    # Prepare chunks data for the LLM
    chunks_data = []
    for chunk in chunks:
        chunks_data.append({
            "chunk_id": chunk.chunk_id,
            "title": chunk.title,
            "text": chunk.text,
            "goal": chunk.goal,
            "setting": chunk.setting,
            "characters": chunk.characters,
            "actions": chunk.actions,
            "props": chunk.props,
            "visual_tags": chunk.visual_tags
        })
    
    # Prepare user prompt
    user_prompt = IMAGE_PROMPTER_USER.format(
        chunks_json=json.dumps(chunks_data, indent=2),
        style_card=refined.style_card.json() if hasattr(refined.style_card, 'json') else str(refined.style_card),
        narrative_brief=refined.narrative_brief.json() if hasattr(refined.narrative_brief, 'json') else str(refined.narrative_brief),
        visual_tags=", ".join(refined.visual_tags) if refined.visual_tags else "educational, child-friendly",
        render_style=refined.style_card.render_style,
        palette=", ".join(refined.style_card.palette),
        character_consistency=refined.style_card.character_consistency
    )
    
    try:
        # Generate panels using LLM
        raw_response = llm_client.generate_json(
            model="gpt-4o",  # Fixed parameter name
            system_prompt=IMAGE_PROMPTER_SYSTEM,
            user_prompt=user_prompt,
            schema_name="PanelsOutput",
            max_tokens=2000,
            temperature=0.7
        )
        
        logger.info(f"Image Prompter raw response: {json.dumps(raw_response, indent=2)}")
        
        # Validate JSON structure  
        try:
            panels_output = PanelsOutput.parse_obj(raw_response)
        except Exception as e:
            logger.error("Panels JSON invalid: %s\nRAW=%s", e, raw_response)
            raise RuntimeError("Image Prompter produced invalid JSON") from e
        
        # Validate panel count matches chunk count
        if len(panels_output.panels) != len(chunks):
            logger.error(f"Panel count ({len(panels_output.panels)}) doesn't match chunk count ({len(chunks)})")
            raise RuntimeError("Panel count must match chunk count")
        
        # Validate each panel has required fields
        for i, panel in enumerate(panels_output.panels):
            if not panel.chunk_id or not panel.positive_prompt or not panel.caption:
                logger.error(f"Panel {i} missing required fields: chunk_id={panel.chunk_id}, prompt={bool(panel.positive_prompt)}, caption={bool(panel.caption)}")
                raise RuntimeError(f"Panel {i} missing required fields")
        
        logger.info(f"Generated {len(panels_output.panels)} panels successfully")
        return panels_output
        
    except Exception as e:
        logger.error(f"Panel generation failed: {e}")
        
        # Fallback to enhanced default panels
        logger.info("Using fallback panel generation")
        return _create_fallback_panels(chunks, refined)


def _create_fallback_panels(chunks: List[ChunkSpec], refined: RefinedPromptSpec) -> PanelsOutput:
    """Create enhanced fallback panels when LLM generation fails."""
    
    panels = []
    
    for i, chunk in enumerate(chunks):
        # Create basic character specification from refined prompt
        character = CharacterSpec(
            name="student", 
            age="6-7", 
            clothes="casual school clothes", 
            hair="brown"
        )
        
        # Build contextual prompts
        positive_prompt = (
            f"{chunk.text}. "
            f"Setting: {chunk.setting}. "
            f"Characters: {', '.join(chunk.characters)}. "
            f"Actions: {', '.join(chunk.actions)}. "
            f"Style: {refined.style_card.render_style}. "
            f"Colors: {', '.join(refined.style_card.palette)}. "
            f"Visual elements: {', '.join(chunk.visual_tags)}"
        )
        
        negative_prompt = "text, watermark, logo, inappropriate content, scary, violent"
        
        # Build panel
        panel = PanelSpec(
            chunk_id=chunk.chunk_id,
            caption=f"{chunk.title}: {chunk.text[:100]}...",
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            reference=ReferenceInstruction(
                use_previous_image=(i > 0),  # First panel doesn't use reference
                purpose="style" if i > 0 else None,  # Fixed: use valid enum value
                strength_hint=0.6 if i > 0 else None
            ),
            continuity_notes=[f"maintain {refined.style_card.character_consistency}", f"consistent {refined.style_card.render_style}"],
            style_card=PanelStyleCard(
                render_style=refined.style_card.render_style,
                palette=refined.style_card.palette,
                camera=refined.style_card.camera,
                aspect_ratio=refined.style_card.aspect_ratio,
                character_sheet=[character]
            ),
            sdxl_hints=SDXLHints(
                width=settings.default_width,
                height=settings.default_height,
                cfg_scale=settings.default_cfg_scale,
                steps=settings.default_steps,
                sampler=settings.default_sampler
            )
        )
        
        panels.append(panel)
    
    return PanelsOutput(panels=panels)
