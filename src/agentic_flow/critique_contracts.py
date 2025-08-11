
from pydantic import BaseModel, Field
from typing import List

from .models import Topic


class CritiqueInput(BaseModel):
    year: str
    subject: str
    refined_prompt: str
    analogy: str
    narrative: str
    resolved_topic: Topic


class CritiqueScores(BaseModel):
    alignment: int = Field(ge=0, le=5, default=5)
    vocab: int = Field(ge=0, le=5, default=5)
    scope: int = Field(ge=0, le=5, default=5)
    cognitive_load: int = Field(ge=0, le=5, default=5)


class CritiqueOutput(BaseModel):
    verdict: str  # Pass | Soft Pass | Fail
    scores: CritiqueScores = CritiqueScores()
    evidence: list[str] = []
    feedback_for_analogy: str = ""
    feedback_for_narrative: str = ""


# New comprehensive critique model for manifest evaluation
class Score(BaseModel):
    """Individual score with feedback and suggestions."""
    score: float = Field(ge=0, le=10, description="Score from 0-10")
    feedback: str = Field(description="Detailed feedback for this dimension")
    suggestions: List[str] = Field(default_factory=list, description="Specific improvement suggestions")


class CritiqueReport(BaseModel):
    """Comprehensive educational content critique report."""
    curriculum_alignment: Score = Field(description="How well content matches learning objectives and stays within scope")
    age_appropriateness: Score = Field(description="Suitability of vocabulary, complexity, and presentation for target age")
    educational_quality: Score = Field(description="Clarity of explanation, examples, and pedagogical scaffolding")
    engagement: Score = Field(description="Interest and motivation potential for learners")
    
    overall_score: float = Field(ge=0, le=10, description="Overall weighted score across all dimensions")
    priority_issues: List[str] = Field(default_factory=list, description="Most critical issues to address first")
    recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations for improvement")
    notes: str = Field(default="", description="Additional notes or context for the evaluation")
