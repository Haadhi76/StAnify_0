"""
Tests for LLM client functionality.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from src.agentic_flow.llm_client import LLMClient, generate_json, JSONParseError, ValidationFailureError
from src.agentic_flow.refined_prompt_contracts import RefinedPromptSpec


class TestLLMClient:
    """Test LLM client functionality."""
    
    def test_llm_client_init(self):
        """Test LLM client initialization."""
        client = LLMClient(max_retries=5, retry_delay=2.0)
        assert client.max_retries == 5
        assert client.retry_delay == 2.0
    
    def test_generate_json_valid_response(self):
        """Test successful JSON generation."""
        client = LLMClient()
        
        # Mock successful LLM call
        with patch.object(client, '_call_llm') as mock_call:
            mock_call.return_value = '{"status": "success", "message": "test"}'
            
            result = client.generate_json(
                model="test-model",
                system_prompt="Test system",
                user_prompt="Test user",
                schema_name="TestSchema"
            )
            
            assert result == {"status": "success", "message": "test"}
    
    def test_generate_json_invalid_json_retry(self):
        """Test retry behavior on invalid JSON."""
        client = LLMClient(max_retries=2, retry_delay=0.1)
        
        with patch.object(client, '_call_llm') as mock_call:
            # First call returns invalid JSON, second call succeeds
            mock_call.side_effect = [
                'invalid json',
                '{"status": "success"}'
            ]
            
            result = client.generate_json(
                model="test-model",
                system_prompt="Test system",
                user_prompt="Test user",
                schema_name="TestSchema"
            )
            
            assert result == {"status": "success"}
            assert mock_call.call_count == 2
    
    def test_generate_json_max_retries_exceeded(self):
        """Test behavior when max retries are exceeded."""
        client = LLMClient(max_retries=2, retry_delay=0.1)
        
        with patch.object(client, '_call_llm') as mock_call:
            mock_call.return_value = 'invalid json'
            
            with pytest.raises(JSONParseError):
                client.generate_json(
                    model="test-model",
                    system_prompt="Test system",
                    user_prompt="Test user",
                    schema_name="TestSchema"
                )
    
    def test_generate_json_with_pydantic_validation(self):
        """Test JSON generation with Pydantic model validation."""
        from src.agentic_flow.critique_contracts import CritiqueScores
        
        client = LLMClient()
        
        with patch.object(client, '_call_llm') as mock_call:
            mock_call.return_value = '{"alignment": 5, "vocab": 4, "scope": 3, "cognitive_load": 5}'
            
            result = client.generate_json(
                model="test-model",
                system_prompt="Test system",
                user_prompt="Test user",
                schema_name="CritiqueScores",
                expected_model=CritiqueScores
            )
            
            assert "alignment" in result
            assert result["alignment"] == 5
    
    def test_convenience_function(self):
        """Test convenience function."""
        with patch('src.agentic_flow.llm_client.llm_client') as mock_client:
            mock_client.generate_json.return_value = {"test": "result"}
            
            result = generate_json(
                model="test-model",
                system="Test system",
                user="Test user",
                schema_name="TestSchema"
            )
            
            assert result == {"test": "result"}
            mock_client.generate_json.assert_called_once()


class TestLLMClientStubs:
    """Test stubbed LLM responses."""
    
    def test_refiner_stub_response(self):
        """Test that refiner context returns appropriate stub."""
        client = LLMClient()
        
        response = client._call_llm(
            model="test",
            system_prompt="refiner system prompt for refined_prompt",
            user_prompt="test user prompt"
        )
        
        # Should return valid JSON
        parsed = json.loads(response)
        assert "year" in parsed
        assert "subject" in parsed
        assert "topic_id" in parsed
    
    def test_critique_stub_response(self):
        """Test that critique context returns appropriate stub."""
        client = LLMClient()
        
        response = client._call_llm(
            model="test",
            system_prompt="critique system prompt",
            user_prompt="test user prompt"
        )
        
        # Should return valid JSON
        parsed = json.loads(response)
        assert "verdict" in parsed
        assert "scores" in parsed
        assert "evidence" in parsed
    
    def test_generic_stub_response(self):
        """Test generic stub response."""
        client = LLMClient()
        
        response = client._call_llm(
            model="test",
            system_prompt="generic prompt",
            user_prompt="test user prompt"
        )
        
        # Should return valid JSON
        parsed = json.loads(response)
        assert "status" in parsed
        assert parsed["status"] == "success"
