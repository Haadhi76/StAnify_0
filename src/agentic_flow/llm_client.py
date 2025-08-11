"""
Unified LLM client for JSON-structured generation.
Handles retries, JSON validation, and error handling for all LLM interactions.
"""

import json
import logging
import time
import os
from typing import Any, Dict, Optional, Type, Union

from pydantic import BaseModel, ValidationError

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import OpenAI client
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass


class JSONParseError(LLMError):
    """Raised when LLM response cannot be parsed as JSON."""
    pass


class ValidationFailureError(LLMError):
    """Raised when LLM response doesn't match expected schema."""
    pass


class LLMClient:
    """
    Unified client for LLM interactions with JSON schema enforcement.
    
    Handles:
    - JSON-only response formatting
    - Retry logic for invalid JSON
    - Pydantic model validation
    - Error logging and recovery
    """
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Initialize OpenAI client if available
        if OPENAI_AVAILABLE:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.openai_client = openai.OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized with API key")
            else:
                self.openai_client = None
                logger.warning("OpenAI API key not found in environment")
        else:
            self.openai_client = None
            logger.warning("OpenAI package not available, using stubbed responses")
    
    def generate_json(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        schema_name: str,
        expected_model: Optional[Type[BaseModel]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate JSON response from LLM with validation and retries.
        
        Args:
            model: Model identifier (e.g., "gpt-4", "claude-3-sonnet")
            system_prompt: System message content
            user_prompt: User message content
            schema_name: Name of the expected schema (for error messages)
            expected_model: Optional Pydantic model for validation
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Dict containing the parsed JSON response
            
        Raises:
            JSONParseError: If JSON parsing fails after all retries
            ValidationFailureError: If response doesn't match expected schema
            LLMError: For other LLM-related errors
        """
        
        # Enhanced system prompt to enforce JSON-only responses
        json_system_prompt = f"""{system_prompt}

CRITICAL: You must respond with valid JSON only. No explanations, no markdown formatting, no code blocks.
Expected schema: {schema_name}
Start your response with {{ and end with }}."""
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Call the actual LLM (stubbed for now)
                raw_response = self._call_llm(
                    model=model,
                    system_prompt=json_system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                # Parse JSON
                try:
                    response_data = json.loads(raw_response.strip())
                except json.JSONDecodeError as e:
                    raise JSONParseError(f"Invalid JSON in response: {e}") from e
                
                # Validate against Pydantic model if provided
                if expected_model:
                    try:
                        # Validate using Pydantic model
                        validated = expected_model(**response_data)
                        # Return the validated data as dict
                        return validated.dict()
                    except ValidationError as e:
                        raise ValidationFailureError(f"Response doesn't match {schema_name} schema: {e}") from e
                
                return response_data
                
            except (JSONParseError, ValidationFailureError) as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    # Final attempt failed
                    break
            
            except Exception as e:
                # Unexpected error - don't retry
                raise LLMError(f"Unexpected error during LLM call: {e}") from e
        
        # All retries exhausted
        raise last_error or LLMError("All retry attempts failed")
    
    def _call_llm(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Make the actual LLM API call.
        Uses OpenAI API if available, otherwise returns stubbed response.
        """
        
        # Use real OpenAI API if available
        if self.openai_client and model.startswith('gpt'):
            try:
                logger.info(f"Making real OpenAI API call to {model}")
                
                # Add JSON format instruction to system prompt
                json_system_prompt = system_prompt + "\n\nIMPORTANT: You must respond with valid JSON only. Do not include any other text."
                
                # Models that support JSON response format
                supports_json_mode = model in ['gpt-4-1106-preview', 'gpt-4-turbo-preview', 'gpt-3.5-turbo-1106', 'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo']
                
                kwargs = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": json_system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens or 2000
                }
                
                if supports_json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                    logger.info(f"Using JSON response format for {model}")
                else:
                    logger.info(f"Model {model} doesn't support JSON format, relying on prompt instruction")
                
                response = self.openai_client.chat.completions.create(**kwargs)
                
                content = response.choices[0].message.content
                logger.info(f"OpenAI API response received ({len(content)} characters)")
                return content
                
            except Exception as e:
                logger.error(f"OpenAI API call failed: {e}")
                logger.warning("Falling back to stubbed response")
                # Fall through to stubbed response
        
        # STUB: Fallback response for development/testing
        logger.info(f"LLM call to {model} (STUBBED)")
        logger.debug(f"System: {system_prompt[:100]}...")
        logger.debug(f"User: {user_prompt[:100]}...")
        
        # Return a minimal valid JSON based on the context
        if "refined_prompt" in system_prompt.lower() or "refiner" in system_prompt.lower():
            return '''{
                "year": "Year 1",
                "subject": "mathematics",
                "topic_id": "add_within_20",
                "topic_title": "Addition within 20 (no regrouping)",
                "learning_objectives": ["Add two numbers within 20"],
                "success_criteria": ["Student can add numbers using fruit or number line"],
                "constraints": {
                    "reading_level": "KS1-simple",
                    "max_steps": 5,
                    "numbers_range": [0, 20],
                    "representations_allowed": ["fruit", "counters", "ten-frame", "number line"],
                    "vocab_prefer": ["add", "plus", "makes", "equals", "sum", "more"],
                    "vocab_avoid": ["regroup", "carry", "algorithm"],
                    "out_of_scope": ["carrying_regrouping", "column_addition", "negative_numbers"]
                },
                "pedagogy": {
                    "activate_prior_knowledge": "Count to 20 and recall number bonds.",
                    "address_misconceptions": ["Equals means 'is the same as'"],
                    "tone_style": "warm, playful"
                },
                "narrative_brief": {
                    "setting": "picnic",
                    "characters": ["child"],
                    "must_include": ["fruit counters"],
                    "must_avoid": ["regrouping"]
                },
                "visual_tags": ["number line", "fruit"],
                "style_card": {
                    "render_style": "2D flat illustration, thick outlines",
                    "palette": ["soft primaries"],
                    "camera": "eye level",
                    "aspect_ratio": "4:3",
                    "character_consistency": "stable clothing colors"
                },
                "notes_for_writers": "Keep steps ≤5 and numbers ≤20."
            }'''
        
        elif "critique" in system_prompt.lower():
            return '''{
                "verdict": "Pass",
                "scores": {
                    "alignment": 5,
                    "vocab": 5,
                    "scope": 5,
                    "cognitive_load": 5
                },
                "evidence": ["Uses allowed representations (fruit, number line)"],
                "feedback_for_analogy": "Good; keep fruit and avoid jargon.",
                "feedback_for_narrative": "Keep numbers ≤20; avoid 'regrouping' term."
            }'''
        
        else:
            # Generic response
            return '{"status": "success", "message": "LLM response stubbed"}'


# Global instance
llm_client = LLMClient()


def generate_json(
    model: str,
    system: str,
    user: str,
    schema_name: str,
    expected_model: Optional[Type[BaseModel]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function for JSON generation.
    
    Args:
        model: Model identifier
        system: System prompt
        user: User prompt  
        schema_name: Schema name for error messages
        expected_model: Optional Pydantic model for validation
        **kwargs: Additional arguments passed to generate_json
        
    Returns:
        Parsed and validated JSON response
    """
    return llm_client.generate_json(
        model=model,
        system_prompt=system,
        user_prompt=user,
        schema_name=schema_name,
        expected_model=expected_model,
        **kwargs
    )
