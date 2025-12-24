"""Main entry point for LinkedIn Profile Scraper."""
import sys
import argparse
import json
import os
import time
import re
from datetime import datetime
from pathlib import Path
import undetected_chromedriver as uc
from apify_client import ApifyClient
from config import OUTPUT_DIR


def extract_profile_id(profile_url: str) -> str:
    """Extract profile identifier from LinkedIn URL."""
    # Match patterns like /in/username/ or /in/username
    match = re.search(r'/in/([^/?]+)', profile_url)
    if match:
        return match.group(1)
    return "unknown_profile"


def get_profile_output_dir(profile_id: str) -> str:
    """Get or create output directory for a specific profile."""
    profile_dir = os.path.join(OUTPUT_DIR, profile_id)
    Path(profile_dir).mkdir(parents=True, exist_ok=True)
    return profile_dir


def save_profile_data(profile_data: dict, profile_dir: str) -> str:
    """Save scraped profile data to JSON file in profile directory."""
    filepath = os.path.join(profile_dir, "profile_data.json")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(profile_data, f, indent=2, ensure_ascii=False)
    
    return filepath


def save_posts_data(posts_data: list, profile_dir: str) -> str:
    """Save scraped posts data to JSON file in profile directory."""
    filepath = os.path.join(profile_dir, "posts.json")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(posts_data, f, indent=2, ensure_ascii=False)
    
    return filepath


def analyze_and_categorize_posts(posts_data: list, profile_id: str, profile_dir: str) -> dict:
    """
    Analyze posts and categorize into original posts, reposts, and quote reposts.
    
    Returns:
        Dictionary with analysis results
    """
    original_posts = []
    reposts = []
    quote_reposts = []
    
    for post in posts_data:
        post_type = post.get('post_type', 'unknown')
        author = post.get('author', {})
        author_username = author.get('username', '')
        
        if post_type == 'quote':
            quote_reposts.append(post)
        elif post_type == 'repost':
            reposts.append(post)
        elif post_type == 'regular':
            if author_username == profile_id or author_username == '':
                original_posts.append(post)
            else:
                reposts.append(post)
        else:
            if author_username == profile_id:
                original_posts.append(post)
            else:
                reposts.append(post)
    
    total = len(posts_data)
    analysis = {
        'statistics': {
            'total_posts': total,
            'original_posts': len(original_posts),
            'reposts': len(reposts),
            'quote_reposts': len(quote_reposts),
            'original_percentage': round(len(original_posts) / total * 100, 1) if total > 0 else 0,
            'repost_percentage': round(len(reposts) / total * 100, 1) if total > 0 else 0,
            'quote_repost_percentage': round(len(quote_reposts) / total * 100, 1) if total > 0 else 0
        },
        'original_posts': original_posts,
        'reposts': reposts,
        'quote_reposts': quote_reposts
    }
    
    # Save analysis
    analysis_file = os.path.join(profile_dir, 'posts_analysis.json')
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    return analysis


def capture_linkedin_page_screenshot(url: str, output_path: str, cookie_data: dict) -> str:
    """
    Generic function to capture screenshot of any LinkedIn page.
    
    Args:
        url: LinkedIn URL to screenshot
        output_path: Full path where screenshot should be saved
        cookie_data: Dictionary containing cookies
        
    Returns:
        Path to saved screenshot
    """
    li_at = cookie_data.get('li_at')
    jsessionid = cookie_data.get('JSESSIONID', '')
    user_agent = cookie_data.get('UserAgent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36')
    
    # Use undetected-chromedriver to avoid bot detection
    options = uc.ChromeOptions()
    # High-resolution screenshot settings (2x scale for retina quality)
    options.add_argument('--window-size=2560,1440')  # Higher base resolution
    options.add_argument('--force-device-scale-factor=2')  # 2x DPI for crisp text
    options.add_argument('--high-dpi-support=1')  # Enable high DPI support
    options.add_argument(f'--user-agent={user_agent}')
    
    driver = uc.Chrome(options=options, headless=True)
    
    try:
        # Go to LinkedIn homepage to set cookies
        driver.get('https://www.linkedin.com')
        time.sleep(2)
        
        # Add authentication cookies
        driver.add_cookie({
            'name': 'li_at',
            'value': li_at,
            'domain': '.linkedin.com',
            'path': '/'
        })
        
        if jsessionid:
            driver.add_cookie({
                'name': 'JSESSIONID',
                'value': jsessionid,
                'domain': '.www.linkedin.com',
                'path': '/'
            })
        
        # Navigate to the target URL
        driver.get(url)
        time.sleep(6)
        
        current_url = driver.current_url
        
        # Check if authentication worked
        if 'login' in current_url or 'authwall' in current_url:
            raise Exception(f"Cookie authentication failed for {url}")
        
        # Scroll to load content
        driver.execute_script("window.scrollTo(0, 500)")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, 1500)")
        time.sleep(1.5)
        driver.execute_script("window.scrollTo(0, 0)")
        time.sleep(1)
        
        # Get full page height and resize (maintain high resolution)
        total_height = driver.execute_script("return document.body.scrollHeight")
        # Use higher width for better quality (2560px base, scaled to 2x = 5120px effective)
        driver.set_window_size(2560, min(total_height + 100, 10000))
        time.sleep(1.5)  # Extra wait for high-res rendering
        
        # Take high-quality screenshot using PNG format
        # This captures at the actual device scale factor (2x = retina quality)
        screenshot_png = driver.get_screenshot_as_png()
        
        # Save with PIL for maximum quality control
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(screenshot_png))
        # Save with maximum quality (no compression for PNG)
        img.save(output_path, 'PNG', optimize=False)
        
    finally:
        driver.quit()
    
    return output_path


def capture_linkedin_screenshot(profile_url: str, profile_dir: str) -> str:
    """Capture full-page screenshot of LinkedIn profile using Selenium + cookie."""
    filepath = os.path.join(profile_dir, "screenshot.png")
    
    # Load cookie
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cookie_file = os.path.join(script_dir, 'linkedin_cookies.json')
    
    with open(cookie_file, 'r') as f:
        cookie_data = json.load(f)
    
    print(f"Using cookie: {cookie_data.get('li_at', '')[:20]}...")
    print("Setting up browser...")
    print("Establishing session...")
    
    capture_linkedin_page_screenshot(profile_url, filepath, cookie_data)
    print(f"Screenshot saved: {filepath}")
    
    return filepath


def capture_original_posts_screenshots(original_posts: list, profile_dir: str) -> list:
    """
    Capture screenshots of all original posts.
    
    Args:
        original_posts: List of original post dictionaries
        profile_dir: Directory to save screenshots
        
    Returns:
        List of dictionaries with post info and screenshot paths
    """
    if not original_posts:
        print("No original posts to screenshot.")
        return []
    
    # Load cookies
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cookie_file = os.path.join(script_dir, 'linkedin_cookies.json')
    
    with open(cookie_file, 'r') as f:
        cookie_data = json.load(f)
    
    # Create posts_screenshots subdirectory
    posts_screenshots_dir = os.path.join(profile_dir, "post_screenshots")
    Path(posts_screenshots_dir).mkdir(parents=True, exist_ok=True)
    
    screenshots_info = []
    
    print(f"\nCapturing screenshots for {len(original_posts)} original posts...")
    
    for i, post in enumerate(original_posts, 1):
        post_url = post.get('url', '')
        if not post_url:
            print(f"  Post {i}: No URL found, skipping...")
            continue
        
        # Extract post ID or use index for filename
        posted_at = post.get('posted_at', {})
        date_str = posted_at.get('date', '').split()[0] if posted_at.get('date') else f'post_{i}'
        date_str = date_str.replace('-', '')  # Remove dashes for filename
        
        screenshot_filename = f"post_{i}_{date_str}.png"
        screenshot_path = os.path.join(posts_screenshots_dir, screenshot_filename)
        
        try:
            print(f"  Post {i}/{len(original_posts)}: Capturing {post_url[:60]}...")
            capture_linkedin_page_screenshot(post_url, screenshot_path, cookie_data)
            
            screenshots_info.append({
                'post_index': i,
                'post_url': post_url,
                'screenshot_path': screenshot_path,
                'screenshot_filename': screenshot_filename,
                'posted_at': posted_at.get('relative', ''),
                'reactions': post.get('stats', {}).get('total_reactions', 0)
            })
            print(f"    ✓ Saved: {screenshot_filename}")
            
        except Exception as e:
            print(f"    ✗ Failed to capture post {i}: {str(e)}")
            screenshots_info.append({
                'post_index': i,
                'post_url': post_url,
                'screenshot_path': None,
                'error': str(e)
            })
    
    return screenshots_info


def main():
    """Main function to orchestrate scraping and screenshot capture."""
    parser = argparse.ArgumentParser(
        description='Scrape LinkedIn profile data and capture screenshot'
    )
    parser.add_argument(
        'profile_url',
        type=str,
        help='LinkedIn profile URL to scrape'
    )
    
    args = parser.parse_args()
    profile_url = args.profile_url
    
    # Validate URL
    if not profile_url.startswith(('http://', 'https://', 'www.')):
        if 'linkedin.com' in profile_url:
            profile_url = 'https://' + profile_url
        else:
            profile_url = 'https://www.linkedin.com/in/' + profile_url
    elif profile_url.startswith('www.'):
        profile_url = 'https://' + profile_url
    
    # Extract profile ID and create dedicated folder
    profile_id = extract_profile_id(profile_url)
    profile_dir = get_profile_output_dir(profile_id)
    
    print(f"Profile ID: {profile_id}")
    print(f"Output directory: {profile_dir}\n")
    
    try:
        # Initialize Apify client for profile data
        print("Initializing Apify client...")
        client = ApifyClient()
        
        # Scrape profile data via Apify
        print(f"Scraping profile data from {profile_url}...")
        profile_data = client.scrape_linkedin_profile(profile_url)
        
        # Save profile data
        print("Saving profile data...")
        data_filepath = save_profile_data(profile_data, profile_dir)
        print(f"✓ Profile data saved to: {data_filepath}")
        
        # Scrape LinkedIn posts via Apify
        print(f"\nScraping LinkedIn posts from {profile_url}...")
        posts_data = client.scrape_linkedin_posts(profile_url)
        
        # Save posts data
        print(f"Saving posts data ({len(posts_data)} posts found)...")
        posts_filepath = save_posts_data(posts_data, profile_dir)
        print(f"✓ Posts data saved to: {posts_filepath}")
        
        # Analyze and categorize posts
        print("Analyzing posts (categorizing reposts vs original posts)...")
        analysis = analyze_and_categorize_posts(posts_data, profile_id, profile_dir)
        stats = analysis['statistics']
        print(f"✓ Analysis complete:")
        print(f"  - Original Posts: {stats['original_posts']} ({stats['original_percentage']}%)")
        print(f"  - Reposts: {stats['reposts']} ({stats['repost_percentage']}%)")
        print(f"  - Quote Reposts: {stats['quote_reposts']} ({stats['quote_repost_percentage']}%)")
        
        # Capture screenshots of original posts (limit to most recent 6)
        original_posts = analysis['original_posts']
        if original_posts:
            # Limit to most recent 6 posts
            original_posts_limited = original_posts[:6]
            if len(original_posts) > 6:
                print(f"Limiting post screenshots to most recent 6 out of {len(original_posts)} original posts...")
            post_screenshots = capture_original_posts_screenshots(original_posts_limited, profile_dir)
            
            # Update analysis with screenshot paths
            for i, post in enumerate(original_posts):
                if i < len(post_screenshots) and post_screenshots[i].get('screenshot_path'):
                    post['screenshot_path'] = post_screenshots[i]['screenshot_path']
                    post['screenshot_filename'] = post_screenshots[i]['screenshot_filename']
            
            # Save updated analysis
            analysis_file = os.path.join(profile_dir, 'posts_analysis.json')
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
            
            print(f"\n✓ Captured {len([s for s in post_screenshots if s.get('screenshot_path')])} post screenshots")
        else:
            print("\nNo original posts to screenshot.")
        
        # Capture LinkedIn profile screenshot using cookies + Selenium
        print(f"\nCapturing LinkedIn profile screenshot...")
        screenshot_filepath = capture_linkedin_screenshot(profile_url, profile_dir)
        print(f"✓ Profile screenshot saved to: {screenshot_filepath}")
        
        # Phase 2: Nano Banana Annotation
        print("\n" + "="*60)
        print("PHASE 2: Nano Banana Annotation")
        print("="*60)
        
        try:
            from nano_banana_annotator import annotate_all
            from generate_email_nano import generate_outreach_email

            print("\nAnnotating screenshots via Google Gemini...")
            annotated_images = annotate_all(profile_dir)
            print(f"✓ Annotated {len(annotated_images)} images")

            # Generate email from annotated images
            print("\nGenerating outreach email...")
            email_result = generate_outreach_email(profile_dir, annotated_images)
            print(f"✓ Email generated!")
            print(f"  Subject: {email_result['subject']}")
            print(f"  Saved to: {email_result['file_path']}")
            
        except ImportError as e:
            print(f"\n⚠️  Warning: Phase 2 modules not available: {e}")
            print("  Make sure OpenAI API key is set in .env file")
        except Exception as e:
            print(f"\n⚠️  Warning: Phase 2 analysis failed: {e}")
            import traceback
            traceback.print_exc()
            print("  Continuing with Phase 1 results only...")
        
        # Print summary
        print("\n" + "="*60)
        print("SUCCESS! Files saved:")
        print(f"  - Profile Folder: {profile_dir}")
        print(f"  - Profile Data:   {data_filepath}")
        print(f"  - Posts Data:      {posts_filepath} ({len(posts_data)} posts)")
        print(f"  - Screenshot:      {screenshot_filepath}")
        nano_dir = os.path.join(profile_dir, "nano_banana_annotated")
        email_path = os.path.join(profile_dir, "outreach_email_nano.html")
        print(f"  - Nano Banana Images: {nano_dir}")
        print(f"  - Outreach Email:     {email_path}")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
