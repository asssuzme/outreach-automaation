"""
Email Generator V3 - Works with Editorial Engine V3 output.

Generates personalized outreach emails using surgical precision teardown results.
"""

import os
import json
import base64
from typing import Dict, Any, List
from config import AGENCY_NAME, AGENCY_EMAIL, AGENCY_WEBSITE


def image_to_base64(image_path: str) -> str:
    """Convert image to base64 data URL."""
    with open(image_path, 'rb') as f:
        data = base64.b64encode(f.read()).decode('utf-8')
        return f"data:image/png;base64,{data}"


def generate_email(profile_dir: str) -> Dict[str, str]:
    """
    Generate outreach email from V3 editorial output.
    
    Args:
        profile_dir: Path to profile directory
        
    Returns:
        Dict with subject, body, file_path
    """
    # Load profile data
    profile_path = os.path.join(profile_dir, 'profile_data.json')
    with open(profile_path, 'r') as f:
        profile_data = json.load(f)
    
    # Load V3 editorial summary
    summary_path = os.path.join(profile_dir, 'editorial_v3', 'summary.json')
    with open(summary_path, 'r') as f:
        summary = json.load(f)
    
    # Get name
    basic_info = profile_data.get('basic_info', {})
    full_name = basic_info.get('fullname', 'there')
    first_name = full_name.split()[0] if full_name else 'there'
    headline = basic_info.get('headline', '')
    
    # Get profile analysis
    profile_analysis = summary.get('profile', {})
    verdict = profile_analysis.get('verdict', 'Your profile needs work')
    the_gap = profile_analysis.get('the_gap', '')
    annotations = profile_analysis.get('annotations', [])
    
    # Get post analyses
    posts = {k: v for k, v in summary.items() if k.startswith('post_') and 'error' not in v}
    
    # Build email
    subject = f"{first_name}, brutal truth about your LinkedIn - {verdict.lower()}"
    
    # Build annotation insights
    insights_html = ""
    for i, ann in enumerate(annotations, 1):
        insights_html += f"""
        <div style="margin: 15px 0; padding: 15px; background: #fff8f8; border-left: 3px solid #c4283a; border-radius: 4px;">
            <div style="font-weight: 600; color: #c4283a; margin-bottom: 5px;">Issue #{i}</div>
            <div style="font-size: 15px; color: #333; margin-bottom: 8px;">"{ann.get('target_text', '')[:80]}..."</div>
            <div style="font-size: 14px; color: #666; font-style: italic;">→ {ann.get('editorial_note', '')}</div>
        </div>"""
    
    # Build posts section
    posts_html = ""
    if posts:
        posts_html = """
        <div style="margin-top: 35px; padding-top: 25px; border-top: 1px solid #eee;">
            <h3 style="font-size: 14px; text-transform: uppercase; letter-spacing: 1px; color: #666; margin-bottom: 20px;">Your Recent Posts</h3>
        """
        for key, post in list(posts.items())[:2]:
            post_verdict = post.get('verdict', '')
            post_gap = post.get('the_gap', '')
            posts_html += f"""
            <div style="margin: 15px 0; padding: 15px; background: #f8f9fa; border-radius: 6px;">
                <div style="font-weight: 600; color: #333; margin-bottom: 8px;">{post_verdict}</div>
                <div style="font-size: 14px; color: #666;">{post_gap}</div>
            </div>"""
        posts_html += "</div>"
    
    # Get teardown image
    profile_img_path = os.path.join(profile_dir, 'editorial_v3', 'profile.png')
    img_html = ""
    if os.path.exists(profile_img_path):
        img_data = image_to_base64(profile_img_path)
        img_html = f"""
        <div style="margin: 30px 0;">
            <div style="font-size: 14px; text-transform: uppercase; letter-spacing: 1px; color: #666; margin-bottom: 15px;">Visual Proof</div>
            <img src="{img_data}" alt="Profile Editorial" style="max-width: 100%; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />
        </div>"""
    
    # Build full HTML
    body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your LinkedIn Profile Review</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.7; color: #333; background: #f5f5f5;">
    
    <div style="max-width: 680px; margin: 0 auto; padding: 20px;">
        <div style="background: white; padding: 45px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.08);">
            
            <!-- Hook -->
            <p style="font-size: 17px; margin: 0 0 20px 0;">Hey {first_name},</p>
            
            <p style="font-size: 16px; margin: 0 0 20px 0;">
                I came across your profile yesterday. I spent about 10 minutes going through it — your headline, your about section, your posts.
            </p>
            
            <p style="font-size: 16px; margin: 0 0 25px 0;">
                And honestly? <strong>I have thoughts.</strong>
            </p>
            
            <!-- The Verdict Box -->
            <div style="background: #1a1a1a; color: white; padding: 25px 30px; border-radius: 8px; margin: 30px 0;">
                <div style="font-size: 12px; text-transform: uppercase; letter-spacing: 2px; opacity: 0.7; margin-bottom: 10px;">The Verdict</div>
                <div style="font-size: 24px; font-weight: 700;">{verdict}</div>
            </div>
            
            <!-- The Gap -->
            <p style="font-size: 16px; margin: 25px 0; color: #444;">
                {the_gap}
            </p>
            
            <!-- Annotations / Insights -->
            <div style="margin: 30px 0;">
                <div style="font-size: 14px; text-transform: uppercase; letter-spacing: 1px; color: #666; margin-bottom: 15px;">Where It Falls Apart</div>
                {insights_html}
            </div>
            
            <!-- Visual Proof -->
            {img_html}
            
            <!-- Posts -->
            {posts_html}
            
            <!-- The Transition -->
            <div style="margin: 40px 0; padding: 25px; background: #f8fafc; border-radius: 8px; border-left: 4px solid #0077b5;">
                <p style="font-size: 16px; margin: 0 0 15px 0;">
                    <strong>Here's the thing:</strong> You clearly have substance. You're doing real work.
                </p>
                <p style="font-size: 16px; margin: 0;">
                    But your profile doesn't communicate that. It reads like a list of things you've done, not a story someone wants to follow.
                </p>
            </div>
            
            <!-- CTA -->
            <div style="background: linear-gradient(135deg, #0077b5 0%, #005885 100%); color: white; padding: 35px; border-radius: 10px; margin-top: 35px; text-align: center;">
                <p style="font-size: 18px; margin: 0 0 15px 0; font-weight: 600;">
                    I run {AGENCY_NAME}.
                </p>
                <p style="font-size: 15px; margin: 0 0 25px 0; opacity: 0.95; line-height: 1.7;">
                    We help people like you transform their LinkedIn presence from forgettable to magnetic. Not generic tips — real strategy that opens doors.
                </p>
                <a href="mailto:{AGENCY_EMAIL}?subject=Let's talk about my LinkedIn" 
                   style="display: inline-block; background: white; color: #0077b5; padding: 14px 35px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px;">
                    Let's Talk
                </a>
            </div>
            
            <!-- Footer -->
            <div style="text-align: center; margin-top: 40px; padding-top: 25px; border-top: 1px solid #eee; color: #888; font-size: 13px;">
                <p style="margin: 0 0 8px 0;"><strong>{AGENCY_NAME}</strong></p>
                <p style="margin: 0 0 8px 0;"><a href="mailto:{AGENCY_EMAIL}" style="color: #0077b5; text-decoration: none;">{AGENCY_EMAIL}</a></p>
                <p style="margin: 0;"><a href="{AGENCY_WEBSITE}" style="color: #0077b5; text-decoration: none;">{AGENCY_WEBSITE}</a></p>
                <p style="margin-top: 20px; font-size: 11px; color: #aaa; font-style: italic;">
                    Not interested? No worries. Just ignore this — no follow-ups, I promise.
                </p>
            </div>
            
        </div>
    </div>
    
</body>
</html>"""
    
    # Save email
    email_path = os.path.join(profile_dir, 'outreach_email_v3.html')
    with open(email_path, 'w', encoding='utf-8') as f:
        f.write(body)
    
    print(f"\n✅ Email Generated!")
    print(f"   Subject: {subject}")
    print(f"   Saved to: {email_path}")
    
    return {
        'subject': subject,
        'body': body,
        'file_path': email_path
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        profile_dir = sys.argv[1]
        result = generate_email(profile_dir)
    else:
        print("Usage: python generate_email_v3.py <profile_dir>")
        print("Example: python generate_email_v3.py output/jainjatin2525")





