#!/usr/bin/env python3
"""Test OpenAI API key validation."""

import os
from src.agentic_flow.llm_client import llm_client

def test_openai_key():
    """Test if the new OpenAI API key is working."""
    print("=== Testing OpenAI API Key ===")
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print(f"API Key loaded: {api_key[:10]}...{api_key[-4:]} (length: {len(api_key)})")
    else:
        print("❌ No API key found in environment")
        return
    
    # Test a simple API call
    try:
        response = llm_client.chat_completion([
            {"role": "user", "content": "Say 'API key working' if you can read this."}
        ], max_tokens=10)
        
        if response and "API key working" in response:
            print("✅ OpenAI API key is working correctly")
        else:
            print(f"⚠️ Unexpected response: {response}")
    except Exception as e:
        print(f"❌ API key test failed: {e}")

if __name__ == "__main__":
    test_openai_key()
