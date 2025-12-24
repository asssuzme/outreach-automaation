#!/usr/bin/env python3
"""
Batch Processor for LinkedIn Outreach Automation

Processes multiple LinkedIn profiles through the full pipeline:
1. Scrape profile data (Apify)
2. Scrape posts data (Apify)
3. Capture screenshots (profile + posts)
4. Annotate screenshots (Nano Banana)
5. Generate outreach email
6. Send LinkedIn message (optional)

Usage:
    # Process profiles from a file (one URL per line)
    python batch_processor.py --profiles-file profiles.txt
    
    # Process profiles from command line
    python batch_processor.py --profiles "url1,url2,url3"
    
    # Process profiles and send messages
    python batch_processor.py --profiles-file profiles.txt --send-messages
    
    # Skip annotation (if already done)
    python batch_processor.py --profiles-file profiles.txt --skip-annotation
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Import main workflow components
from main import (
    extract_profile_id, get_profile_output_dir, 
    save_profile_data, save_posts_data,
    analyze_and_categorize_posts, capture_original_posts_screenshots,
    capture_linkedin_screenshot
)
from apify_client import ApifyClient
from send_with_photos import send_message_with_photos


class BatchProcessor:
    """Process multiple LinkedIn profiles through the full outreach pipeline."""
    
    def __init__(self, delay_between_profiles: int = 30, delay_between_messages: int = 60):
        """
        Initialize batch processor.
        
        Args:
            delay_between_profiles: Seconds to wait between processing profiles
            delay_between_messages: Seconds to wait between sending messages
        """
        self.delay_between_profiles = delay_between_profiles
        self.delay_between_messages = delay_between_messages
        self.results = []
        self.client = ApifyClient()
        
    def normalize_profile_url(self, url: str) -> str:
        """Normalize LinkedIn profile URL."""
        url = url.strip()
        if not url:
            return None
        
        # Handle various formats
        if url.startswith(('http://', 'https://')):
            return url
        elif url.startswith('www.'):
            return 'https://' + url
        elif 'linkedin.com' in url:
            return 'https://' + url if not url.startswith('http') else url
        else:
            # Assume it's a username
            return f'https://www.linkedin.com/in/{url}'
    
    def load_profiles_from_file(self, file_path: str) -> List[str]:
        """Load profile URLs from a text file (one per line)."""
        profiles = []
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):  # Skip empty lines and comments
                    profiles.append(self.normalize_profile_url(line))
        return profiles
    
    def process_single_profile(
        self, 
        profile_url: str,
        skip_scraping: bool = False,
        skip_annotation: bool = False,
        skip_screenshot: bool = False
    ) -> Dict:
        """
        Process a single profile through the full pipeline.
        
        Returns:
            Dictionary with processing results and status
        """
        result = {
            'profile_url': profile_url,
            'profile_id': None,
            'profile_dir': None,
            'status': 'pending',
            'errors': [],
            'warnings': [],
            'started_at': datetime.now().isoformat(),
            'completed_at': None,
            'steps_completed': []
        }
        
        try:
            # Extract profile ID
            profile_id = extract_profile_id(profile_url)
            profile_dir = get_profile_output_dir(profile_id)
            result['profile_id'] = profile_id
            result['profile_dir'] = profile_dir
            
            print(f"\n{'='*80}")
            print(f"PROCESSING PROFILE: {profile_id}")
            print(f"URL: {profile_url}")
            print(f"{'='*80}\n")
            
            # Step 1: Scrape profile data
            if not skip_scraping:
                print("[1/5] Scraping profile data...")
                try:
                    profile_data = self.client.scrape_linkedin_profile(profile_url)
                    save_profile_data(profile_data, profile_dir)
                    result['steps_completed'].append('scrape_profile')
                    print("✓ Profile data scraped")
                except Exception as e:
                    error_msg = f"Failed to scrape profile: {str(e)}"
                    result['errors'].append(error_msg)
                    print(f"✗ {error_msg}")
                    result['status'] = 'failed'
                    return result
            else:
                print("[1/5] Skipping profile scraping (using existing data)")
                result['steps_completed'].append('scrape_profile_skipped')
            
            # Step 2: Scrape posts data
            if not skip_scraping:
                print("[2/5] Scraping posts data...")
                try:
                    posts_data = self.client.scrape_linkedin_posts(profile_url)
                    save_posts_data(posts_data, profile_dir)
                    
                    # Analyze posts
                    analysis = analyze_and_categorize_posts(posts_data, profile_id, profile_dir)
                    stats = analysis['statistics']
                    print(f"✓ Posts scraped: {stats['original_posts']} original, {stats['reposts']} reposts")
                    result['steps_completed'].append('scrape_posts')
                except Exception as e:
                    warning_msg = f"Failed to scrape posts: {str(e)}"
                    result['warnings'].append(warning_msg)
                    print(f"⚠ {warning_msg}")
            else:
                print("[2/5] Skipping posts scraping")
                result['steps_completed'].append('scrape_posts_skipped')
            
            # Step 3: Capture screenshots
            if not skip_screenshot:
                print("[3/5] Capturing screenshots...")
                try:
                    # Capture profile screenshot
                    screenshot_path = capture_linkedin_screenshot(profile_url, profile_dir)
                    print(f"✓ Profile screenshot saved")
                    
                    # Capture post screenshots (if posts exist)
                    posts_file = os.path.join(profile_dir, 'posts_analysis.json')
                    if os.path.exists(posts_file):
                        with open(posts_file, 'r') as f:
                            analysis = json.load(f)
                        original_posts = analysis.get('original_posts', [])[:6]  # Limit to 6
                        if original_posts:
                            post_screenshots = capture_original_posts_screenshots(original_posts, profile_dir)
                            print(f"✓ Captured {len([s for s in post_screenshots if s.get('screenshot_path')])} post screenshots")
                    result['steps_completed'].append('screenshots')
                except Exception as e:
                    error_msg = f"Failed to capture screenshots: {str(e)}"
                    result['errors'].append(error_msg)
                    print(f"✗ {error_msg}")
                    result['status'] = 'failed'
                    return result
            else:
                print("[3/5] Skipping screenshot capture")
                result['steps_completed'].append('screenshots_skipped')
            
            # Step 4: Annotate screenshots
            if not skip_annotation:
                print("[4/5] Annotating screenshots...")
                try:
                    from nano_banana_annotator import annotate_all
                    annotated_images = annotate_all(profile_dir)
                    print(f"✓ Annotated {len(annotated_images)} images")
                    result['steps_completed'].append('annotation')
                    result['annotated_images'] = list(annotated_images.keys())
                except Exception as e:
                    error_msg = f"Failed to annotate: {str(e)}"
                    result['errors'].append(error_msg)
                    print(f"✗ {error_msg}")
                    # Don't fail completely - continue without annotation
                    result['warnings'].append(error_msg)
            else:
                print("[4/5] Skipping annotation")
                result['steps_completed'].append('annotation_skipped')
            
            # Step 5: Generate outreach email
            print("[5/5] Generating outreach email...")
            try:
                from generate_email_nano import generate_outreach_email
                annotated_images = result.get('annotated_images', [])
                if annotated_images:
                    # Reconstruct annotated_images dict
                    nano_dir = os.path.join(profile_dir, 'nano_banana_annotated')
                    annotated_dict = {}
                    for key in annotated_images:
                        img_path = os.path.join(nano_dir, key)
                        if os.path.exists(img_path):
                            annotated_dict[key] = img_path
                    email_result = generate_outreach_email(profile_dir, annotated_dict)
                    print(f"✓ Email generated: {email_result.get('subject', 'N/A')}")
                    result['steps_completed'].append('email_generation')
                else:
                    print("⚠ No annotated images - skipping email generation")
                    result['warnings'].append("No annotated images for email generation")
            except Exception as e:
                warning_msg = f"Failed to generate email: {str(e)}"
                result['warnings'].append(warning_msg)
                print(f"⚠ {warning_msg}")
            
            result['status'] = 'completed'
            result['completed_at'] = datetime.now().isoformat()
            print(f"\n✅ Profile {profile_id} processed successfully!")
            
        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(f"Unexpected error: {str(e)}")
            result['completed_at'] = datetime.now().isoformat()
            print(f"\n✗ Failed to process profile: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return result
    
    def send_message_for_profile(self, profile_dir: str) -> bool:
        """Send LinkedIn message for a processed profile."""
        try:
            # Load profile data
            profile_data_path = os.path.join(profile_dir, 'profile_data.json')
            if not os.path.exists(profile_data_path):
                print(f"✗ Profile data not found: {profile_data_path}")
                return False
            
            with open(profile_data_path, 'r') as f:
                profile = json.load(f)
            
            profile_url = profile.get('basic_info', {}).get('profile_url')
            if not profile_url:
                print("✗ Profile URL not found in profile data")
                return False
            
            first_name = profile.get('basic_info', {}).get('first_name', 'there')
            
            # Generate professional agency-focused message
            message = f"""Hey {first_name}! 👋

I run a personal branding agency, and I personally took some time to do a complete breakdown of your LinkedIn profile. 

I've attached an annotated snapshot that shows exactly where your profile is losing people and what specific fixes would make the biggest impact.

I'd love to discuss this further with you - happy to hop on a quick call to walk you through the full breakdown and answer any questions. Would that be helpful?"""
            
            # Get annotated images
            images = []
            nano_dir = os.path.join(profile_dir, 'nano_banana_annotated')
            if os.path.exists(nano_dir):
                profile_img = os.path.join(nano_dir, 'profile.png')
                if os.path.exists(profile_img):
                    images.append(profile_img)
            
            if not images:
                print("⚠ No annotated images found - skipping message")
                return False
            
            # Send message
            print(f"\n📤 Sending LinkedIn message to {first_name}...")
            success = send_message_with_photos(profile_url, message, images)
            
            if success:
                print(f"✅ Message sent successfully!")
                return True
            else:
                print(f"✗ Failed to send message")
                return False
                
        except Exception as e:
            print(f"✗ Error sending message: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def process_batch(
        self,
        profile_urls: List[str],
        send_messages: bool = True,  # Default to True - send messages automatically
        skip_scraping: bool = False,
        skip_annotation: bool = False,
        skip_screenshot: bool = False
    ) -> Dict:
        """
        Process multiple profiles in batch.
        
        Returns:
            Dictionary with batch processing results
        """
        total = len(profile_urls)
        print(f"\n{'='*80}")
        print(f"BATCH PROCESSING: {total} profiles")
        print(f"{'='*80}\n")
        
        batch_result = {
            'total_profiles': total,
            'processed': 0,
            'succeeded': 0,
            'failed': 0,
            'messages_sent': 0,
            'started_at': datetime.now().isoformat(),
            'results': []
        }
        
        for i, profile_url in enumerate(profile_urls, 1):
            print(f"\n{'='*80}")
            print(f"PROFILE {i}/{total}")
            print(f"{'='*80}")
            
            # Process profile
            result = self.process_single_profile(
                profile_url,
                skip_scraping=skip_scraping,
                skip_annotation=skip_annotation,
                skip_screenshot=skip_screenshot
            )
            batch_result['results'].append(result)
            batch_result['processed'] += 1
            
            if result['status'] == 'completed':
                batch_result['succeeded'] += 1
                
                # Send message if requested
                if send_messages:
                    print(f"\n⏳ Waiting {self.delay_between_messages} seconds before sending message...")
                    time.sleep(self.delay_between_messages)
                    
                    if self.send_message_for_profile(result['profile_dir']):
                        batch_result['messages_sent'] += 1
            else:
                batch_result['failed'] += 1
            
            # Wait before next profile (except for last one)
            if i < total:
                print(f"\n⏳ Waiting {self.delay_between_profiles} seconds before next profile...")
                time.sleep(self.delay_between_profiles)
        
        batch_result['completed_at'] = datetime.now().isoformat()
        
        # Print summary
        print(f"\n{'='*80}")
        print("BATCH PROCESSING COMPLETE")
        print(f"{'='*80}")
        print(f"Total profiles: {batch_result['total_profiles']}")
        print(f"Processed: {batch_result['processed']}")
        print(f"Succeeded: {batch_result['succeeded']}")
        print(f"Failed: {batch_result['failed']}")
        if send_messages:
            print(f"Messages sent: {batch_result['messages_sent']}")
        print(f"{'='*80}\n")
        
        return batch_result


def main():
    parser = argparse.ArgumentParser(
        description="Batch process LinkedIn profiles through outreach automation pipeline"
    )
    parser.add_argument(
        '--profiles-file',
        type=str,
        help='Path to text file with profile URLs (one per line)'
    )
    parser.add_argument(
        '--profiles',
        type=str,
        help='Comma-separated list of profile URLs'
    )
    parser.add_argument(
        '--no-send-messages',
        action='store_true',
        help='Skip sending LinkedIn messages (default: messages are sent automatically)'
    )
    parser.add_argument(
        '--skip-scraping',
        action='store_true',
        help='Skip scraping step (use existing data)'
    )
    parser.add_argument(
        '--skip-annotation',
        action='store_true',
        help='Skip annotation step'
    )
    parser.add_argument(
        '--skip-screenshot',
        action='store_true',
        help='Skip screenshot capture step'
    )
    parser.add_argument(
        '--delay-profiles',
        type=int,
        default=30,
        help='Seconds to wait between profiles (default: 30)'
    )
    parser.add_argument(
        '--delay-messages',
        type=int,
        default=60,
        help='Seconds to wait between messages (default: 60)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Save batch results to JSON file'
    )
    
    args = parser.parse_args()
    
    # Get profile URLs
    profile_urls = []
    
    if args.profiles_file:
        if not os.path.exists(args.profiles_file):
            print(f"✗ Profiles file not found: {args.profiles_file}")
            sys.exit(1)
        processor = BatchProcessor(
            delay_between_profiles=args.delay_profiles,
            delay_between_messages=args.delay_messages
        )
        profile_urls = processor.load_profiles_from_file(args.profiles_file)
    elif args.profiles:
        processor = BatchProcessor(
            delay_between_profiles=args.delay_profiles,
            delay_between_messages=args.delay_messages
        )
        profile_urls = [processor.normalize_profile_url(url) for url in args.profiles.split(',')]
    else:
        print("✗ Error: Must provide either --profiles-file or --profiles")
        parser.print_help()
        sys.exit(1)
    
    if not profile_urls:
        print("✗ No valid profile URLs found")
        sys.exit(1)
    
    # Process batch (send_messages defaults to True unless --no-send-messages is used)
    send_messages = not args.no_send_messages
    
    batch_result = processor.process_batch(
        profile_urls,
        send_messages=send_messages,
        skip_scraping=args.skip_scraping,
        skip_annotation=args.skip_annotation,
        skip_screenshot=args.skip_screenshot
    )
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(batch_result, f, indent=2)
        print(f"✓ Batch results saved to: {args.output}")


if __name__ == "__main__":
    main()

