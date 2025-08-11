"""
Prompt Refiner agent using LLM client for structured generation.
Takes user input and curriculum knowledge to create detailed prompt specifications.
"""

import logging
from pathlib import Path
from typing import Dict, Any

from .models import Topic
from .llm_client import generate_json
from .refined_prompt_contracts import RefinedPromptSpec
from .settings import settings

logger = logging.getLogger(__name__)

# Template paths
TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
REFINER_SYSTEM_TEMPLATE = TEMPLATES_DIR / "refiner_system.txt"
REFINER_USER_TEMPLATE = TEMPLATES_DIR / "refiner_user.txt"


class PromptRefinerAgent:
    """
    Agent for refining user prompts into detailed educational content specifications.
    
    Uses LLM to transform user requests into structured RefinedPromptSpec objects
    with appropriate constraints, pedagogy, and style guidance.
    """
    
    def __init__(self, model: str = None):
        self.model = model or settings.llm_model
        
        # Load templates
        self.system_template = self._load_template(REFINER_SYSTEM_TEMPLATE)
        self.user_template = self._load_template(REFINER_USER_TEMPLATE)
    
    def _load_template(self, template_path: Path) -> str:
        """Load template file with error handling."""
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.warning(f"Template not found: {template_path}, using fallback")
            return self._get_fallback_template(template_path.name)
    
    def _get_fallback_template(self, template_name: str) -> str:
        """Provide fallback templates if files are missing."""
        
        if "system" in template_name:
            return """You are an expert educational content specialist. Your task is to refine user prompts into detailed educational specifications.

You will receive:
1. User's educational request/prompt
2. Curriculum data for the target year and subject
3. Topic information with constraints and vocabulary

Your output must be a JSON object matching the RefinedPromptSpec schema with:
- Clear learning objectives and success criteria
- Age-appropriate constraints (reading level, complexity)
- Pedagogical guidance (prior knowledge, misconceptions)
- Visual style specifications for illustrations
- Narrative brief for storytelling context

Focus on educational effectiveness, age-appropriateness, and clear visual communication."""
        
        elif "user" in template_name:
            return """Please refine this educational request into a detailed specification:

**User Request:** {user_prompt}

**Target Audience:** {year} {subject}

**Topic Context:**
Title: {topic_title}
Topic ID: {topic_id}
Known Vocabulary: {vocab_known}
Avoid Vocabulary: {vocab_avoid}
Representations: {representations}
Out of Scope: {out_of_scope}
Typical Misconceptions: {misconceptions}

**Style Guidance:**
Reading Level: {reading_level}
Max Steps: {max_steps}
Number Range: {numbers_range}

Please create a comprehensive RefinedPromptSpec that captures the educational intent while respecting the constraints and making the content engaging for the target age group."""
        
        else:
            return "Template not available."
    
    def refine_prompt(
        self,
        user_prompt: str,
        year: str,
        subject: str,
        topic: Topic
    ) -> RefinedPromptSpec:
        """
        Refine user prompt into detailed educational specification.
        
        Args:
            user_prompt: Original user request
            year: Target year/grade level
            subject: Subject area
            topic: Curriculum topic information (Topic model)
            
        Returns:
            RefinedPromptSpec with detailed educational guidance
            
        Raises:
            Exception: If LLM generation fails
        """
        
        try:
            # Format user template with context from Topic model
            user_message = self.user_template.format(
                user_prompt=user_prompt,
                year=year,
                subject=subject,
                topic_title=topic.title,
                topic_id=topic.id,
                vocab_known=", ".join(topic.vocab_known),
                vocab_avoid=", ".join(topic.vocab_avoid),
                representations=", ".join(topic.representations_allowed),
                out_of_scope=", ".join(topic.out_of_scope),
                misconceptions=", ".join(topic.typical_misconceptions),
                reading_level=topic.style_guidance.reading_level,
                max_steps=topic.style_guidance.max_steps,
                numbers_range=topic.style_guidance.numbers_range or [0, 100]
            )
            
            logger.info(f"Refining prompt for {year} {subject}: {user_prompt[:50]}...")
            
            # Generate structured response
            response_data = generate_json(
                model=self.model,
                system=self.system_template,
                user=user_message,
                schema_name="RefinedPromptSpec",
                expected_model=RefinedPromptSpec,
                temperature=0.7
            )
            
            # Create RefinedPromptSpec from response
            refined_spec = RefinedPromptSpec(**response_data)
            
            logger.info(f"Successfully refined prompt: {refined_spec.topic_title}")
            return refined_spec
            
        except Exception as e:
            logger.error(f"Failed to refine prompt: {e}")
            
            # Fallback to basic specification
            logger.warning("Using fallback prompt specification")
            return self._create_fallback_spec(user_prompt, year, subject, topic)
    
    def _create_fallback_spec(
        self,
        user_prompt: str,
        year: str,
        subject: str,
        topic: Topic
    ) -> RefinedPromptSpec:
        """Create a basic fallback specification when LLM fails."""
        
        from .refined_prompt_contracts import (
            Constraints, NarrativeBrief, Pedagogy, StyleCard
        )
        
        return RefinedPromptSpec(
            year=year,
            subject=subject,
            topic_id=topic.id,
            topic_title=topic.title,
            learning_objectives=[f"Understand {topic.title}"],  # Generated from topic
            success_criteria=[f"Can demonstrate understanding of {topic.title}"],
            constraints=Constraints(
                reading_level=topic.style_guidance.reading_level,
                max_steps=topic.style_guidance.max_steps,
                numbers_range=topic.style_guidance.numbers_range or [0, 100],
                representations_allowed=topic.representations_allowed,
                vocab_prefer=topic.vocab_known[:6],  # First 6
                vocab_avoid=topic.vocab_avoid,
                out_of_scope=topic.out_of_scope
            ),
            pedagogy=Pedagogy(
                activate_prior_knowledge="Review foundational concepts",
                address_misconceptions=topic.typical_misconceptions[:2] if topic.typical_misconceptions else ["Common errors in this topic"],
                tone_style="clear and engaging"
            ),
            narrative_brief=NarrativeBrief(
                setting="learning environment",
                characters=["student"],
                must_include=["learning materials"],
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
            notes_for_writers=f"Simplified fallback for: {user_prompt[:30]}..."
        )


# Global instance
prompt_refiner = PromptRefinerAgent()


def refine_user_prompt(
    user_prompt: str,
    year: str,
    subject: str,
    topic: Topic
) -> RefinedPromptSpec:
    """
    Convenience function for prompt refinement.
    
    Args:
        user_prompt: User's educational request
        year: Target year level
        subject: Subject area
        topic: Curriculum topic data (Topic model)
        
    Returns:
        Refined educational specification
    """
    return prompt_refiner.refine_prompt(user_prompt, year, subject, topic)
