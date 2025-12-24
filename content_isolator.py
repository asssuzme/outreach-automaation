"""
Content Isolator - Clean crop, no analysis, just canvas prep.

Purpose: Get a clean canvas for the editorial teardown.
- Crops to main content column only
- Preserves full post/profile section integrity
- No annotations, no markers, no thinking here

Output: clean_content.png
"""

import os
import base64
import json
from PIL import Image
from typing import Dict, Any, Optional, Tuple
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_VISION_MODEL


class ContentIsolator:
    """Isolates main content from LinkedIn screenshots."""
    
    PADDING = 40  # pixels of padding around cropped content - generous
    SKIP_CROP = True  # Don't crop aggressively - just use original with minimal trim
    
    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API key required")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def _get_image_dimensions(self, image_path: str) -> Tuple[int, int]:
        """Get image width and height."""
        with Image.open(image_path) as img:
            return img.size
    
    def _detect_content_bounds(self, image_path: str, content_type: str = "profile") -> Dict[str, int]:
        """
        Use GPT-4 Vision to detect the main content boundaries.
        
        Args:
            image_path: Path to the screenshot
            content_type: "profile" or "post"
            
        Returns:
            Dict with x1, y1, x2, y2 coordinates
        """
        width, height = self._get_image_dimensions(image_path)
        base64_image = self._encode_image(image_path)
        
        if content_type == "profile":
            content_description = """the main LinkedIn profile card/section. This includes:
            - Profile photo, name, headline
            - About section
            - Experience section
            - Education section
            
            EXCLUDE:
            - Left navigation sidebar
            - Right sidebar (ads, suggestions, "People also viewed")
            - Top navigation bar
            - Footer
            - Any promotional content"""
        else:
            content_description = """the main LinkedIn post content. This includes:
            - Author info (photo, name, headline)
            - Post text/content
            - Any images/media in the post
            - Engagement bar (likes, comments count)
            
            EXCLUDE:
            - Left sidebar (your profile mini card)
            - Right sidebar (ads, suggestions)
            - Top navigation bar
            - "See who's hiring" or similar promotional sections
            - Other posts above/below
            - Comments section"""
        
        prompt = f"""Analyze this LinkedIn screenshot and identify the EXACT pixel boundaries of {content_description}

Image dimensions: {width}px wide x {height}px tall

Return ONLY valid JSON with the bounding box coordinates:
{{
    "x1": <left edge in pixels>,
    "y1": <top edge in pixels>,
    "x2": <right edge in pixels>,
    "y2": <bottom edge in pixels>
}}

Be precise. The goal is to crop ONLY the main content, removing all LinkedIn UI chrome.
Return raw JSON only, no markdown formatting."""

        response = self.client.chat.completions.create(
            model=OPENAI_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=200
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean up response
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result_text = result_text.strip()
        
        try:
            bounds = json.loads(result_text)
            # Validate bounds
            bounds["x1"] = max(0, int(bounds.get("x1", 0)))
            bounds["y1"] = max(0, int(bounds.get("y1", 0)))
            bounds["x2"] = min(width, int(bounds.get("x2", width)))
            bounds["y2"] = min(height, int(bounds.get("y2", height)))
            return bounds
        except json.JSONDecodeError:
            # Fallback: use center 60% of image width
            margin_x = int(width * 0.2)
            return {
                "x1": margin_x,
                "y1": 0,
                "x2": width - margin_x,
                "y2": height
            }
    
    def isolate_content(self, input_path: str, output_path: str, 
                        content_type: str = "profile") -> Optional[str]:
        """
        Isolate main content from a LinkedIn screenshot.
        
        For V0: MINIMAL cropping. Keep most of the content visible.
        We only trim obvious sidebars if they're clearly separate.
        
        Args:
            input_path: Path to the raw screenshot
            output_path: Path where clean content will be saved
            content_type: "profile" or "post"
            
        Returns:
            Path to the clean content image, or None if failed
        """
        if not os.path.exists(input_path):
            print(f"  [!] Input image not found: {input_path}")
            return None
        
        with Image.open(input_path) as img:
            width, height = img.size
            
            # CONSERVATIVE cropping - just trim edges, keep everything visible
            if content_type == "post":
                # For posts: trim left sidebar (usually ~70px) and right sidebar (usually last ~250px)
                # But keep it generous - don't cut content
                left_margin = min(50, int(width * 0.03))  # Very small left trim
                right_margin = min(100, int(width * 0.05))  # Small right trim
                x1 = left_margin
                x2 = width - right_margin
                y1 = 0
                y2 = height  # Keep full height
            else:
                # For profile: minimal trimming, keep the full page
                left_margin = min(30, int(width * 0.02))
                right_margin = min(30, int(width * 0.02))
                x1 = left_margin
                x2 = width - right_margin
                y1 = 0
                y2 = height
            
            # Crop
            cropped = img.crop((x1, y1, x2, y2))
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save
            cropped.save(output_path, "PNG")
            
        return output_path
    
    def isolate_profile(self, input_path: str, output_dir: str) -> Optional[str]:
        """Convenience method for profile screenshots."""
        output_path = os.path.join(output_dir, "clean_profile.png")
        return self.isolate_content(input_path, output_path, "profile")
    
    def isolate_post(self, input_path: str, output_dir: str, post_id: int) -> Optional[str]:
        """Convenience method for post screenshots."""
        output_path = os.path.join(output_dir, f"clean_post_{post_id}.png")
        return self.isolate_content(input_path, output_path, "post")


def isolate_all_content(profile_dir: str) -> Dict[str, str]:
    """
    Isolate content from all screenshots in a profile directory.
    
    Args:
        profile_dir: Path to the profile output directory
        
    Returns:
        Dict mapping content type to clean image path
    """
    isolator = ContentIsolator()
    clean_dir = os.path.join(profile_dir, "clean_content")
    os.makedirs(clean_dir, exist_ok=True)
    
    results = {}
    
    # Process profile screenshot (screenshot.png in root)
    profile_screenshot = os.path.join(profile_dir, "screenshot.png")
    if os.path.exists(profile_screenshot):
        print("  Isolating profile content...")
        clean_path = isolator.isolate_profile(profile_screenshot, clean_dir)
        if clean_path:
            results["profile"] = clean_path
            print(f"    ✓ Saved: {clean_path}")
    else:
        print(f"  [!] Profile screenshot not found: {profile_screenshot}")
    
    # Process post screenshots (in post_screenshots/ folder)
    post_screenshots_dir = os.path.join(profile_dir, "post_screenshots")
    if os.path.exists(post_screenshots_dir):
        post_files = sorted([f for f in os.listdir(post_screenshots_dir) 
                             if f.startswith("post_") and f.endswith(".png")])
        
        for i, post_file in enumerate(post_files, 1):
            post_path = os.path.join(post_screenshots_dir, post_file)
            print(f"  Isolating post {i} content...")
            clean_path = isolator.isolate_post(post_path, clean_dir, i)
            if clean_path:
                results[f"post_{i}"] = clean_path
                print(f"    ✓ Saved: {clean_path}")
    else:
        print(f"  [!] No post screenshots directory found")
    
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        profile_dir = sys.argv[1]
        print(f"Isolating content from: {profile_dir}")
        results = isolate_all_content(profile_dir)
        print(f"\nIsolated {len(results)} images")
    else:
        print("Usage: python content_isolator.py <profile_dir>")

