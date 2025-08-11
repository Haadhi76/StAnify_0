#!/usr/bin/env python3
"""Debug API access issues."""

from src.agentic_flow.image_service import ImageService
import requests

def debug_api_access():
    """Debug current API access status."""
    print("=== Debugging API Access ===")
    
    service = ImageService()
    
    print(f"Backend: {service._active_backend}")
    print(f"Mode: {service.config.get('stability_mode')}")
    print(f"API URL: {service.config.get('stability_url')}")
    
    # Test balance
    try:
        balance = service._get_stability_balance()
        if balance is not None:
            print(f"API Balance: ${balance:.6f}")
        else:
            print("Balance check failed")
    except Exception as e:
        print(f"Balance error: {e}")
    
    # Test basic connectivity
    try:
        headers = service._stability_headers()
        response = requests.get(f"{service.config['stability_url']}/v1/user/account", 
                              headers=headers, timeout=10)
        print(f"Account endpoint status: {response.status_code}")
        if response.status_code != 200:
            print(f"Response: {response.text[:500]}")
    except Exception as e:
        print(f"Connectivity error: {e}")

if __name__ == "__main__":
    debug_api_access()
