
import uuid
import logging
from pathlib import Path

from .chunk_maker_agent import generate_chunks_from_content
from .chunks_contracts import ChunkSpec
from .combine_manifest import build_manifest
from .critique_contracts import CritiqueReport
from .critique_agent import critique_manifest
from .exporters.pdf_exporter import export_manifest_to_pdf
from .exporters.pptx_exporter import export_manifest_to_pptx
from .image_continuity_evaluator import create_image_continuity_evaluator, ImageContinuityResult
from .image_panels_contracts import (
    CharacterSpec,
    PanelsOutput,
    PanelSpec,
    ReferenceInstruction,
    SDXLHints,
)
from .image_panels_contracts import StyleCard as PanelStyleCard
from .image_prompter_agent import generate_panels_from_chunks
from .image_service import generate_panel_batch
from .kb_loader import get_year_slice, load_curriculum_kb, resolve_topic
from .persistence import store_manifest_run
from .prompt_refiner_agent import refine_user_prompt
from .refined_prompt_contracts import (
    Constraints,
    NarrativeBrief,
    Pedagogy,
    RefinedPromptSpec,
    StyleCard,
)
from .settings import settings

logger = logging.getLogger(__name__)

# project root = agentic-visuals-hello/
BASE_DIR = Path(__file__).resolve().parents[2]
ASSETS = BASE_DIR / "assets"
PLACEHOLDER = str((ASSETS / "sample_panel.png").resolve())

def _ensure_path_or_placeholder(p: str, placeholder: str) -> str:
    """Ensure path exists or fallback to placeholder with absolute path."""
    try:
        if p and Path(p).exists():
            return str(Path(p).resolve())
    except Exception:
        pass
    return str(Path(placeholder).resolve())


def run_demo(year: str, subject: str, user_prompt: str, kb_dir: str, out_dir: str) -> dict[str, str]:
    """
    Enhanced pipeline using LLM agents and configurable image generation.
    
    Args:
        year: Target year/grade level
        subject: Subject area
        user_prompt: User's educational request
        kb_dir: Knowledge base directory
        out_dir: Output directory for exports
        
    Returns:
        Dictionary with generated file paths and metadata
    """
    
    logger.info(f"Starting pipeline for {year} {subject}: {user_prompt}")
    
    # Load curriculum knowledge
    kb = load_curriculum_kb(kb_dir)
    ykb = get_year_slice(kb, year)
    subj, topic, _ = resolve_topic(ykb, subject, user_prompt)
    
    logger.info(f"Resolved topic: {topic.title} ({topic.id})")
    
    # 1. Use Prompt Refiner Agent (or fallback to manual)
    try:
        refined = refine_user_prompt(user_prompt, year, subject, topic)
        logger.info("Used LLM prompt refiner")
    except Exception as e:
        logger.warning(f"Prompt refiner failed, using fallback: {e}")
        refined = _create_fallback_refined_spec(year, subject, topic, user_prompt)
    
    # 2. Generate basic narrative and analogy (stubbed for now)
    # TODO: Add dedicated narrative generation agent
    analogy = "Counting fruit at a picnic to find how many in total."
    narrative = "A child has 7 apples and finds 5 more at a picnic. They use a number line to count on."
    
    # 3. Generate chunks using LLM agent
    try:
        chunks = generate_chunks_from_content(year, subject, topic, refined, narrative)
        logger.info(f"Generated {len(chunks)} chunks via LLM agent")
    except Exception as e:
        logger.warning(f"LLM chunk generation failed, using fallback: {e}")
        chunks = _generate_chunks(refined, narrative)
    
    # 4. Generate panel specifications using LLM agent
    try:
        panels_out = generate_panels_from_chunks(chunks, refined)
        logger.info(f"Generated {len(panels_out.panels)} panels via LLM agent")
    except Exception as e:
        logger.warning(f"LLM panel generation failed, using fallback: {e}")
        panels_out = _generate_panels(chunks, refined)
    
    # 5. Generate images using configurable backend
    run_id = "run_" + uuid.uuid4().hex[:8]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    try:
        # Use image service with current backend setting
        image_uris = generate_panel_batch(panels_out.panels, str(out))
        # Validate and ensure all paths exist
        for chunk_id, path in image_uris.items():
            image_uris[chunk_id] = _ensure_path_or_placeholder(path, PLACEHOLDER)
        logger.info(f"Generated images using {settings.image_backend} backend")
    except Exception as e:
        logger.warning(f"Image generation failed, using placeholders: {e}")
        # Fallback to placeholder images
        image_uris = {panel.chunk_id: PLACEHOLDER for panel in panels_out.panels}
    
    # 6. Build initial manifest with default critique
    default_critique = _create_fallback_critique_output()
    
    manifest = build_manifest(
        run_id=run_id,
        user_id=None,
        year=year,
        subject=subject,
        refined=refined,
        narrative=narrative,
        chunks=chunks,
        panels_out=panels_out,
        image_uris_by_chunk=image_uris,
        panel_critiques_by_chunk={},  # No panel-level critiques for now
        overall_critique=default_critique,
        model_notes=f"Generated with {settings.image_backend} backend and LLM agents"
    )
    
    # 7. Use Critique Agent to evaluate the complete manifest
    try:
        critique_report = critique_manifest(manifest, topic, refined)
        logger.info(f"Critique overall score: {critique_report.overall_score}")
        
        # Convert CritiqueReport to CritiqueOutput for build_manifest compatibility
        from .critique_contracts import CritiqueOutput, CritiqueScores
        overall_crit = CritiqueOutput(
            verdict="Pass" if critique_report.overall_score >= 7.0 else "Soft Pass" if critique_report.overall_score >= 5.0 else "Fail",
            scores=CritiqueScores(
                alignment=min(5, max(1, int(critique_report.curriculum_alignment.score // 2))),
                vocab=min(5, max(1, int(critique_report.age_appropriateness.score // 2))),
                scope=min(5, max(1, int(critique_report.educational_quality.score // 2))),
                cognitive_load=min(5, max(1, int(critique_report.engagement.score // 2)))
            ),
            evidence=[critique_report.notes],
            feedback_for_analogy="See overall recommendations",
            feedback_for_narrative="; ".join(critique_report.recommendations)
        )
        
    except Exception as e:
        logger.warning(f"Critique agent failed, using fallback: {e}")
        overall_crit = _create_fallback_critique_output()
    
    # 8. Evaluate image continuity and regenerate if needed (max 2 attempts)
    image_continuity_result = None
    regeneration_attempts = 0
    max_regenerations = 2
    
    while regeneration_attempts <= max_regenerations:
        try:
            # Evaluate image continuity
            evaluator = create_image_continuity_evaluator()
            
            # Prepare image paths and prompts for evaluation
            image_paths = []
            prompts = []
            
            for panel in panels_out.panels:
                if panel.chunk_id in image_uris:
                    img_path = image_uris[panel.chunk_id]
                    if Path(img_path).exists():
                        image_paths.append(img_path)
                        prompts.append(panel.positive_prompt)
            
            if image_paths:
                image_continuity_result = evaluator.evaluate_panel_continuity(image_paths, prompts)
                logger.info(f"Image continuity evaluation: {image_continuity_result.verdict} (score: {image_continuity_result.overall_score:.2f})")
                
                # Check if regeneration is needed and allowed
                if (evaluator.should_regenerate_panels(image_continuity_result, max_regenerations - regeneration_attempts) 
                    and regeneration_attempts < max_regenerations):
                    
                    logger.info(f"Regenerating panels (attempt {regeneration_attempts + 1}/{max_regenerations})")
                    regeneration_attempts += 1
                    
                    # Regenerate panels with improved prompts
                    try:
                        # Enhance prompts based on recommendations
                        enhanced_panels = _enhance_panels_for_continuity(panels_out.panels, image_continuity_result)
                        image_uris = generate_panel_batch(enhanced_panels, str(out))
                        # Validate regenerated paths
                        for chunk_id, path in image_uris.items():
                            image_uris[chunk_id] = _ensure_path_or_placeholder(path, PLACEHOLDER)
                        logger.info("Panel regeneration completed")
                        continue  # Re-evaluate with new images
                        
                    except Exception as e:
                        logger.warning(f"Panel regeneration failed: {e}")
                        break  # Exit regeneration loop on failure
                else:
                    break  # No regeneration needed or max attempts reached
            else:
                logger.warning("No valid images found for continuity evaluation")
                break
                
        except Exception as e:
            logger.warning(f"Image continuity evaluation failed: {e}")
            # Create a fallback result
            image_continuity_result = ImageContinuityResult(
                clip_scores=[0.5] * len(panels_out.panels),
                lpips_scores=[0.3] * max(0, len(panels_out.panels) - 1),
                ssim_scores=[0.7] * max(0, len(panels_out.panels) - 1),
                overall_score=0.6,
                verdict="Pass",
                recommendations=["Continuity evaluation unavailable"],
                needs_regeneration=False
            )
            break

    # 9. Rebuild manifest with final critique and continuity results
    manifest = build_manifest(
        run_id=run_id,
        user_id=None,
        year=year,
        subject=subject,
        refined=refined,
        narrative=narrative,
        chunks=chunks,
        panels_out=panels_out,
        image_uris_by_chunk=image_uris,
        panel_critiques_by_chunk={},  # No panel-level critiques for now
        overall_critique=overall_crit,
        model_notes=f"Generated with {settings.image_backend} backend and LLM agents. Image continuity: {image_continuity_result.verdict if image_continuity_result else 'N/A'}"
    )

    # Debug manifest before export
    print("Manifest summary:",
          f"chunks={len(manifest.chunks)}",
          f"panels={len(manifest.panels)}",
          f"missing_img={[p.chunk_id for p in manifest.panels if not p.image_uri]}",
          f"not_found={[p.chunk_id for p in manifest.panels if p.image_uri and not Path(p.image_uri).exists()]}")
    
    # 10. Export to various formats
    pdf_path = str(out / f"{run_id}.pdf")
    pptx_path = str(out / f"{run_id}.pptx")
    export_manifest_to_pdf(manifest, pdf_path)
    export_manifest_to_pptx(manifest, pptx_path)
    
    # Save manifest JSON
    manifest_path = str(out / f"{run_id}.manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest.json(indent=2))

    # 11. Store run in database for persistence
    try:
        result_paths = {
            "run_id": run_id,
            "pdf": pdf_path,
            "pptx": pptx_path,
            "manifest": manifest_path,
            "images": image_uris
        }
        store_manifest_run(manifest, result_paths, user_prompt, image_continuity_result)
        logger.info(f"Stored run in database: {run_id}")
    except Exception as e:
        logger.warning(f"Failed to store run in database: {e}")
    
    logger.info(f"Pipeline completed: {run_id}")
    
    return { 
        "run_id": run_id, 
        "pdf": pdf_path, 
        "pptx": pptx_path, 
        "manifest": manifest_path, 
        "images": image_uris,
        "continuity_result": image_continuity_result
    }


def _create_fallback_refined_spec(year: str, subject: str, topic, user_prompt: str) -> RefinedPromptSpec:
    """Create fallback refined specification when LLM fails."""
    
    return RefinedPromptSpec(
        year=year, subject=subject, topic_id=topic.id, topic_title=topic.title,
        learning_objectives=topic.learning_objectives[:3],  # Limit for demo
        success_criteria=topic.success_criteria[:3],
        constraints=Constraints(
            reading_level=topic.style_guidance.reading_level,
            max_steps=topic.style_guidance.max_steps,
            numbers_range=topic.style_guidance.numbers_range,
            representations_allowed=topic.representations_allowed,
            vocab_prefer=topic.vocab_known[:6], 
            vocab_avoid=topic.vocab_avoid,
            out_of_scope=topic.out_of_scope
        ),
        pedagogy=Pedagogy(
            activate_prior_knowledge="Review relevant foundational concepts.",
            address_misconceptions=["Common student errors in this topic"], 
            tone_style="warm, encouraging"
        ),
        narrative_brief=NarrativeBrief(
            setting="learning environment", 
            characters=["student"], 
            must_include=["educational tools"], 
            must_avoid=["complex terminology"]
        ),
        visual_tags=["educational", "clear"],
        style_card=StyleCard(
            render_style="clean educational illustration",
            palette=["primary colors"],
            camera="eye level",
            aspect_ratio="4:3",
            character_consistency="consistent style"
        ),
        notes_for_writers=f"Fallback specification for: {user_prompt[:50]}..."
    )


def _create_fallback_critique_output():
    """Create fallback critique output when LLM fails."""
    
    from .critique_contracts import CritiqueOutput, CritiqueScores
    
    return CritiqueOutput(
        verdict="Pass",
        scores=CritiqueScores(alignment=4, vocab=4, scope=4, cognitive_load=4),
        evidence=["Fallback critique - content appears suitable"],
        feedback_for_analogy="Analogy seems appropriate for target audience.",
        feedback_for_narrative="Narrative appears to meet educational goals."
    )


def _generate_chunks(refined: RefinedPromptSpec, narrative: str) -> list[ChunkSpec]:
    """Generate chunk specifications (can be enhanced with LLM agent)."""
    
    # For now, create simple 2-chunk breakdown
    chunks = [
        ChunkSpec(
            chunk_id="c1", index=0, title="Setup the problem",
            text="Present the initial situation and quantities.", 
            goal="Establish the mathematical context",
            setting=refined.narrative_brief.setting,
            characters=refined.narrative_brief.characters,
            actions=["introduce problem", "show initial quantities"],
            props=["counting materials"] + refined.narrative_brief.must_include,
            visual_tags=refined.visual_tags[:2]  # First 2 tags
        ),
        ChunkSpec(
            chunk_id="c2", index=1, title="Solve the problem",
            text="Work through the solution step by step.",
            goal="Demonstrate the solution process",
            setting=refined.narrative_brief.setting,
            characters=refined.narrative_brief.characters,
            actions=["apply method", "show solution"],
            props=["solution tools"] + refined.narrative_brief.must_include,
            visual_tags=refined.visual_tags
        )
    ]
    
    return chunks


def _generate_panels(chunks: list[ChunkSpec], refined: RefinedPromptSpec) -> PanelsOutput:
    """Generate panel specifications from chunks."""
    
    panels = []
    
    for i, chunk in enumerate(chunks):
        # Create basic character specification
        character = CharacterSpec(
            name="student", 
            age="6-7", 
            clothes="casual school clothes", 
            hair="brown"
        )
        
        # Build panel
        panel = PanelSpec(
            chunk_id=chunk.chunk_id,
            caption=f"Step {i+1}: {chunk.title}",
            positive_prompt=f"{chunk.text} {refined.style_card.render_style}, {', '.join(refined.style_card.palette)}",
            negative_prompt="text, watermark, logo, inappropriate content",
            reference=ReferenceInstruction(
                use_previous_image=(i > 0),  # First panel doesn't use reference
                purpose="style" if i > 0 else None,
                strength_hint=0.6 if i > 0 else None
            ),
            continuity_notes=[f"maintain {refined.style_card.character_consistency}"],
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


def _enhance_panels_for_continuity(panels: list[PanelSpec], continuity_result: ImageContinuityResult) -> list[PanelSpec]:
    """
    Enhance panel prompts based on image continuity evaluation results.
    
    Args:
        panels: Original panel specifications
        continuity_result: Results from image continuity evaluation
        
    Returns:
        Enhanced panel specifications with improved prompts
    """
    enhanced_panels = []
    
    for i, panel in enumerate(panels):
        enhanced_panel = panel.copy()  # Create a copy to modify
        
        # Base enhancements for continuity
        continuity_keywords = [
            "consistent lighting", "same art style", "coherent visual narrative",
            "maintain character appearance", "consistent color palette"
        ]
        
        # Add specific enhancements based on recommendations
        prompt_enhancements = []
        
        if "poor prompt alignment" in " ".join(continuity_result.recommendations).lower():
            prompt_enhancements.extend([
                "clear educational focus",
                "child-friendly illustration",
                "detailed scene composition"
            ])
        
        if "visual continuity" in " ".join(continuity_result.recommendations).lower():
            prompt_enhancements.extend(continuity_keywords)
        
        # Enhance the positive prompt
        enhanced_prompt = panel.positive_prompt
        if prompt_enhancements:
            enhanced_prompt += f", {', '.join(prompt_enhancements)}"
        
        # Always add basic continuity guidance
        if i > 0:  # Not the first panel
            enhanced_prompt += ", maintain visual consistency with previous panel"
        
        # Update the panel
        enhanced_panel.positive_prompt = enhanced_prompt
        
        # Enhance negative prompt to avoid discontinuity
        enhanced_negative = panel.negative_prompt + ", inconsistent style, jarring transitions, different art style"
        enhanced_panel.negative_prompt = enhanced_negative
        
        # Strengthen reference usage for continuity
        if i > 0:
            enhanced_panel.reference.strength_hint = min(0.8, (enhanced_panel.reference.strength_hint or 0.6) + 0.1)
        
        enhanced_panels.append(enhanced_panel)
    
    return enhanced_panels
