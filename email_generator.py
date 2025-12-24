"""
Email Generator - Uses teardown output to create outreach emails.

The email IS the playbook. The image is just proof.

Structure:
1. Personal hook (short, direct)
2. The verdict (one sentence, stings)
3. Visual proof (minimal teardown image)
4. Why it fails (3 bullets)
5. The fix (ONE direction)
6. Before → After (specific rewrites)
7. CTA (personal, not salesy)
"""

import os
import base64
import json
from typing import Dict, Any, List, Optional
from config import AGENCY_NAME, AGENCY_EMAIL, AGENCY_WEBSITE


class EmailGenerator:
    """Generate emails using teardown output."""
    
    def __init__(self, agency_name: str = None, agency_email: str = None,
                 agency_website: str = None):
        self.agency_name = agency_name or AGENCY_NAME
        self.agency_email = agency_email or AGENCY_EMAIL
        self.agency_website = agency_website or AGENCY_WEBSITE
    
    def image_to_base64(self, image_path: str) -> str:
        """Convert image to base64 for embedding."""
        with open(image_path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('utf-8')
            ext = os.path.splitext(image_path)[1].lower()
            mime = {'png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}.get(ext, 'image/png')
            return f"data:{mime};base64,{data}"
    
    def generate_from_teardown(self, profile_dir: str) -> Dict[str, str]:
        """
        Generate email from teardown output.
        
        Args:
            profile_dir: Path to profile output directory
            
        Returns:
            Dict with subject, body, file_path
        """
        # Load required data
        profile_data = self._load_json(os.path.join(profile_dir, 'profile_data.json'))
        playbooks = self._load_json(os.path.join(profile_dir, 'playbooks.json'))
        diagnoses = self._load_json(os.path.join(profile_dir, 'diagnoses.json'))
        
        # Get profile info
        basic_info = profile_data.get('basic_info', {})
        full_name = basic_info.get('fullname', 'there')
        first_name = full_name.split()[0] if full_name else 'there'
        
        # Get profile playbook (primary)
        profile_playbook = playbooks.get('profile', {})
        profile_diagnosis = diagnoses.get('profile', {})
        
        # Get teardown images
        teardown_dir = os.path.join(profile_dir, 'editorial_teardown')
        teardown_images = {}
        if os.path.exists(teardown_dir):
            for f in os.listdir(teardown_dir):
                if f.endswith('.png'):
                    key = f.replace('_teardown.png', '')
                    teardown_images[key] = os.path.join(teardown_dir, f)
        
        # Generate email
        subject = self._generate_subject(first_name, profile_playbook)
        body = self._generate_body(first_name, profile_playbook, profile_diagnosis, 
                                   teardown_images, playbooks)
        
        # Save email
        email_path = os.path.join(profile_dir, 'outreach_email.html')
        with open(email_path, 'w', encoding='utf-8') as f:
            f.write(f"<!--\nSubject: {subject}\n-->\n{body}")
        
        # Save subject separately
        with open(os.path.join(profile_dir, 'email_subject.txt'), 'w') as f:
            f.write(subject)
        
        return {
            'subject': subject,
            'body': body,
            'file_path': email_path
        }
    
    def _load_json(self, path: str) -> Dict:
        """Load JSON file or return empty dict."""
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return {}
    
    def _generate_subject(self, first_name: str, playbook: Dict) -> str:
        """Generate subject line from playbook."""
        verdict = playbook.get('editorial_verdict', '')
        
        # Extract key word from verdict for subject
        if 'forgettable' in verdict.lower():
            return f"{first_name}, your LinkedIn profile is forgettable - here's why"
        elif 'resume' in verdict.lower():
            return f"{first_name}, your profile reads like a resume - not a brand"
        elif 'credible' in verdict.lower():
            return f"{first_name}, credible but invisible - let's fix that"
        elif 'achievements' in verdict.lower():
            return f"{first_name}, strong achievements, weak story - quick fix"
        else:
            return f"{first_name}, I reviewed your profile - here's the honest truth"
    
    def _generate_body(self, first_name: str, playbook: Dict, diagnosis: Dict,
                       images: Dict[str, str], all_playbooks: Dict) -> str:
        """Generate HTML email body."""
        
        verdict = playbook.get('editorial_verdict', 'Your profile needs work.')
        why_it_fails = playbook.get('why_it_fails', [])
        the_fix = playbook.get('the_fix', '')
        before_after = playbook.get('before_after', {})
        principle = playbook.get('reusable_principle', '')
        
        # Build sections
        fails_html = self._build_fails_section(why_it_fails)
        fix_html = self._build_fix_section(the_fix)
        rewrite_html = self._build_rewrite_section(before_after)
        images_html = self._build_images_section(images)
        posts_html = self._build_posts_section(all_playbooks)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.7;
            color: #333;
            max-width: 680px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 8px;
        }}
        .verdict {{
            font-size: 20px;
            font-weight: 600;
            color: #1a1a1a;
            padding: 25px;
            background: #fafafa;
            border-left: 4px solid #D32F2F;
            margin: 30px 0;
        }}
        .section {{
            margin: 30px 0;
        }}
        .section-title {{
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #666;
            margin-bottom: 15px;
        }}
        .fails-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .fails-list li {{
            padding: 12px 0;
            border-bottom: 1px solid #eee;
            font-size: 16px;
        }}
        .fails-list li:before {{
            content: "—";
            color: #D32F2F;
            margin-right: 10px;
        }}
        .fix-box {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            font-size: 17px;
        }}
        .rewrite {{
            background: #fafafa;
            padding: 20px;
            border-radius: 6px;
            margin: 15px 0;
        }}
        .rewrite-label {{
            font-size: 12px;
            text-transform: uppercase;
            color: #888;
            margin-bottom: 8px;
        }}
        .before {{
            color: #999;
            text-decoration: line-through;
            margin-bottom: 10px;
        }}
        .after {{
            color: #1a1a1a;
            font-weight: 500;
        }}
        .proof-img {{
            max-width: 100%;
            border: 1px solid #ddd;
            border-radius: 6px;
            margin: 15px 0;
        }}
        .cta {{
            background: #0077b5;
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-top: 40px;
            text-align: center;
        }}
        .cta a {{
            background: white;
            color: #0077b5;
            padding: 14px 30px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            display: inline-block;
            margin-top: 20px;
        }}
        .principle {{
            font-style: italic;
            color: #555;
            padding: 20px;
            border-left: 3px solid #0077b5;
            background: #f8fafc;
            margin: 30px 0;
        }}
        .footer {{
            text-align: center;
            color: #888;
            font-size: 13px;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }}
    </style>
</head>
<body>
    <div class="container">
        
        <!-- Hook -->
        <p>Hey {first_name},</p>
        
        <p>I stumbled across your LinkedIn profile and spent 10 minutes looking through it. Not because I was impressed — but because I kept trying to figure out what you actually do and why I should care.</p>
        
        <p>I couldn't. And that's a problem.</p>
        
        <!-- The Verdict -->
        <div class="verdict">
            "{verdict}"
        </div>
        
        <!-- Why It Fails -->
        {fails_html}
        
        <!-- Visual Proof -->
        {images_html}
        
        <!-- The Fix -->
        {fix_html}
        
        <!-- Before/After -->
        {rewrite_html}
        
        <!-- Posts (if any) -->
        {posts_html}
        
        <!-- Principle -->
        {f'<div class="principle">{principle}</div>' if principle else ''}
        
        <!-- CTA -->
        <div class="cta">
            <p style="margin: 0 0 15px 0; font-size: 18px;">I run {self.agency_name}.</p>
            <p style="margin: 0; font-size: 15px; opacity: 0.9;">We help people like you build personal brands that actually open doors. Not generic LinkedIn tips. Real strategy. Real results.</p>
            <a href="mailto:{self.agency_email}?subject=Let's talk about my profile">Let's talk</a>
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <p><strong>{self.agency_name}</strong></p>
            <p><a href="mailto:{self.agency_email}" style="color: #0077b5;">{self.agency_email}</a></p>
            <p style="font-size: 11px; color: #aaa; margin-top: 15px;">Not interested? Just ignore this. No follow-ups.</p>
        </div>
        
    </div>
</body>
</html>"""
        
        return html
    
    def _build_fails_section(self, fails: List[str]) -> str:
        """Build the 'why it fails' section."""
        if not fails:
            return ''
        
        items = '\n'.join([f'<li>{f}</li>' for f in fails[:3]])
        
        return f"""
        <div class="section">
            <div class="section-title">Why It Fails</div>
            <ul class="fails-list">
                {items}
            </ul>
        </div>"""
    
    def _build_fix_section(self, fix: str) -> str:
        """Build the 'the fix' section."""
        if not fix:
            return ''
        
        return f"""
        <div class="section">
            <div class="section-title">The Fix</div>
            <div class="fix-box">{fix}</div>
        </div>"""
    
    def _build_rewrite_section(self, before_after: Dict) -> str:
        """Build the before/after rewrite section."""
        if not before_after:
            return ''
        
        html = '<div class="section"><div class="section-title">Before → After</div>'
        
        headline = before_after.get('headline', {})
        if headline.get('before') and headline.get('after'):
            html += f"""
            <div class="rewrite">
                <div class="rewrite-label">Headline</div>
                <div class="before">{headline['before']}</div>
                <div class="after">{headline['after']}</div>
            </div>"""
        
        paragraph = before_after.get('paragraph', {})
        if paragraph.get('before') and paragraph.get('after'):
            html += f"""
            <div class="rewrite">
                <div class="rewrite-label">Key Section</div>
                <div class="before">{paragraph['before'][:200]}{'...' if len(paragraph.get('before', '')) > 200 else ''}</div>
                <div class="after">{paragraph['after'][:200]}{'...' if len(paragraph.get('after', '')) > 200 else ''}</div>
            </div>"""
        
        html += '</div>'
        return html
    
    def _build_images_section(self, images: Dict[str, str]) -> str:
        """Build the visual proof section with images."""
        if not images:
            return ''
        
        html = '<div class="section"><div class="section-title">Visual Proof</div>'
        
        # Profile image first
        if 'profile' in images and os.path.exists(images['profile']):
            try:
                img_data = self.image_to_base64(images['profile'])
                html += f'<img src="{img_data}" alt="Profile teardown" class="proof-img" />'
            except:
                pass
        
        html += '</div>'
        return html
    
    def _build_posts_section(self, all_playbooks: Dict) -> str:
        """Build section for post analyses if relevant."""
        post_playbooks = {k: v for k, v in all_playbooks.items() if k.startswith('post_')}
        
        if not post_playbooks:
            return ''
        
        # Only include if we have meaningful post feedback
        html = '<div class="section"><div class="section-title">Your Posts</div>'
        
        for key, playbook in list(post_playbooks.items())[:2]:  # Max 2 posts
            verdict = playbook.get('editorial_verdict', '')
            if verdict:
                html += f'<p style="margin: 10px 0; color: #555;"><strong>Post:</strong> "{verdict}"</p>'
        
        html += '</div>'
        return html


def generate_outreach_email(profile_dir: str, analysis: Dict[str, Any] = None,
                           annotated_images: Dict[str, str] = None) -> Dict[str, str]:
    """
    Convenience function - uses teardown output if available, falls back to old method.
    
    Args:
        profile_dir: Profile directory path
        analysis: (Legacy) Analysis results - ignored if teardown exists
        annotated_images: (Legacy) Annotated images - ignored if teardown exists
        
    Returns:
        Dictionary with email content and file path
    """
    generator = EmailGenerator()
    
    # Check if teardown output exists
    playbooks_path = os.path.join(profile_dir, 'playbooks.json')
    
    if os.path.exists(playbooks_path):
        # Use new teardown-based generation
        return generator.generate_from_teardown(profile_dir)
    else:
        # Legacy fallback (shouldn't happen with new pipeline)
        raise FileNotFoundError(f"Playbooks not found at {playbooks_path}. Run teardown_engine first.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        profile_dir = sys.argv[1]
        print(f"Generating email for: {profile_dir}")
        result = generate_outreach_email(profile_dir)
        print(f"\nEmail generated!")
        print(f"Subject: {result['subject']}")
        print(f"Saved to: {result['file_path']}")
    else:
        print("Usage: python email_generator.py <profile_dir>")
