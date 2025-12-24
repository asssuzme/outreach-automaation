"""
Email Extractor - Extracts email from Apify profile data.

IMPORTANT: Only uses the official 'email' field from basic_info.
We do NOT extract emails from text - only the Apify-provided email field.
"""

import json
import os
from typing import Dict, Any, Optional


def get_email_from_profile(profile_data: Dict[str, Any]) -> Optional[str]:
    """
    Get email from profile data (only from basic_info.email field).
    
    Args:
        profile_data: Full profile data dictionary from Apify
        
    Returns:
        Email address if found, None otherwise
    """
    email = profile_data.get('basic_info', {}).get('email')
    
    # Only return if it's a valid non-null value
    if email and email != 'null' and email.strip():
        return email.strip()
    
    return None


def check_profile_for_email(profile_dir: str) -> Dict[str, Any]:
    """
    Check if profile has an email from Apify data.
    
    Args:
        profile_dir: Path to profile output directory
        
    Returns:
        Dict with email status and value
    """
    results = {
        'has_email': False,
        'email': None,
        'source': 'apify_basic_info'
    }
    
    # Load profile data
    profile_path = os.path.join(profile_dir, 'profile_data.json')
    if not os.path.exists(profile_path):
        return results
    
    with open(profile_path, 'r') as f:
        profile_data = json.load(f)
    
    # Get email from basic_info.email field only
    email = get_email_from_profile(profile_data)
    
    if email:
        results['has_email'] = True
        results['email'] = email
    
    return results


def update_profile_email_status(profile_dir: str) -> Dict[str, Any]:
    """
    Check and save email status for a profile.
    
    Args:
        profile_dir: Path to profile output directory
        
    Returns:
        Dict with email extraction results
    """
    results = check_profile_for_email(profile_dir)
    
    # Save results
    email_path = os.path.join(profile_dir, 'email_status.json')
    with open(email_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    return results


def check_all_profiles(output_dir: str = "output") -> Dict[str, Dict[str, Any]]:
    """
    Check all profiles in output directory for emails.
    
    Args:
        output_dir: Path to output directory
        
    Returns:
        Dict mapping profile IDs to email status
    """
    all_results = {}
    
    if not os.path.exists(output_dir):
        return all_results
    
    # Iterate through all profile directories
    for item in os.listdir(output_dir):
        profile_dir = os.path.join(output_dir, item)
        if os.path.isdir(profile_dir):
            profile_data_path = os.path.join(profile_dir, 'profile_data.json')
            if os.path.exists(profile_data_path):
                results = check_profile_for_email(profile_dir)
                all_results[item] = results
    
    return all_results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            # Check all profiles
            print("Checking all profiles for Apify-provided emails...\n")
            results = check_all_profiles()
            
            print("="*60)
            print("EMAIL STATUS (Apify basic_info.email field only)")
            print("="*60)
            
            has_email_count = 0
            for profile_id, status in results.items():
                if status['has_email']:
                    has_email_count += 1
                    print(f"✅ {profile_id:30} -> {status['email']}")
                else:
                    print(f"❌ {profile_id:30} -> No email (null)")
            
            print(f"\n{'='*60}")
            print(f"Total Profiles: {len(results)}")
            print(f"With Email: {has_email_count}")
            print(f"Without Email: {len(results) - has_email_count}")
            
        else:
            # Check single profile
            profile_dir = sys.argv[1]
            print(f"Checking email for: {profile_dir}\n")
            
            results = update_profile_email_status(profile_dir)
            
            print("="*50)
            print("EMAIL STATUS")
            print("="*50)
            if results['has_email']:
                print(f"✅ Email Found: {results['email']}")
                print(f"   Source: {results['source']}")
            else:
                print("❌ No email found in Apify data")
                print("   (basic_info.email is null)")
            print(f"\n✓ Status saved to: {os.path.join(profile_dir, 'email_status.json')}")
    else:
        print("Email Extractor - Apify Email Field Only")
        print("\nUsage:")
        print("  python email_extractor.py <profile_dir>")
        print("  python email_extractor.py --all")
        print("\nExamples:")
        print("  python email_extractor.py output/jainjatin2525")
        print("  python email_extractor.py --all")
