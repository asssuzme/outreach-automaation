#!/usr/bin/env python3
"""
Send LinkedIn messages using Apify's Send DM actor.
This bypasses LinkedIn's IP blocking by using Apify's infrastructure.
"""

import os
import json
from apify_client import ApifyClient


def send_linkedin_dm(profile_urls: list, message: str, li_at: str = None, jsessionid: str = None) -> dict:
    """
    Send LinkedIn DM using Apify's addeus/send-dm actor.
    
    Args:
        profile_urls: List of LinkedIn profile URLs to message
        message: Message text (supports {firstName} variable)
        li_at: LinkedIn li_at cookie (uses env var if not provided)
        jsessionid: LinkedIn JSESSIONID cookie (uses env var if not provided)
    
    Returns:
        dict with results
    """
    api_key = os.environ.get('APIFY_API_KEY')
    if not api_key:
        return {"success": False, "error": "APIFY_API_KEY not set"}
    
    li_at = li_at or os.environ.get('LINKEDIN_LI_AT')
    jsessionid = jsessionid or os.environ.get('LINKEDIN_JSESSIONID', '')
    
    if not li_at:
        return {"success": False, "error": "LinkedIn li_at cookie not provided"}
    
    cookies = [
        {"name": "li_at", "value": li_at, "domain": ".linkedin.com"},
    ]
    if jsessionid:
        cookies.append({"name": "JSESSIONID", "value": jsessionid, "domain": ".linkedin.com"})
    
    client = ApifyClient(api_key)
    
    run_input = {
        "cookies": cookies,
        "profileUrls": profile_urls if isinstance(profile_urls, list) else [profile_urls],
        "message": message,
        "proxyConfiguration": {
            "useApifyProxy": True
        }
    }
    
    print(f"\n{'='*60}")
    print("SENDING LINKEDIN MESSAGE VIA APIFY")
    print(f"{'='*60}")
    print(f"Profiles: {len(run_input['profileUrls'])}")
    print(f"Message: {message[:100]}...")
    print(f"{'='*60}\n")
    
    try:
        print("Starting Apify actor run...")
        run = client.actor("addeus/send-dm").call(run_input=run_input)
        
        print(f"Actor run ID: {run.get('id')}")
        print(f"Status: {run.get('status')}")
        
        results = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results.append(item)
            print(f"Result: {json.dumps(item, indent=2)}")
        
        return {
            "success": True,
            "run_id": run.get("id"),
            "status": run.get("status"),
            "results": results
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python apify_message_sender.py <profile_url> [message]")
        sys.exit(1)
    
    profile_url = sys.argv[1]
    message = sys.argv[2] if len(sys.argv) > 2 else "Hi {firstName}! I came across your profile and thought we should connect. Would love to chat!"
    
    result = send_linkedin_dm([profile_url], message)
    print(f"\nFinal result: {json.dumps(result, indent=2)}")
    
    sys.exit(0 if result.get("success") else 1)
