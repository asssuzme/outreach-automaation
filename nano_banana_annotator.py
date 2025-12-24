"""
Nano Banana Annotator - LinkedIn profile annotation using official Google Gemini API

Supports multiple backends:
1. "gemini_native" - Official Gemini Nano Banana API (gemini-2.5-flash-image) - Fast, 1024px
2. "gemini_native_pro" - Official Gemini Nano Banana Pro API (gemini-3-pro-image-preview) - Up to 4K
3. "gemini_hybrid" - Gemini 2.5 Flash text model for analysis + PIL rendering (FREE fallback)
4. "kie" - KIE.ai nano-banana-pro (paid, no quota limits)

Official API docs: https://ai.google.dev/gemini-api/docs/image-generation
"""

import base64
import glob
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Literal

import requests
from PIL import Image, ImageDraw, ImageFont

from config import (
    KIE_AI_API_KEY, KIE_AI_BASE_URL,
    GEMINI_API_KEY, GEMINI_TEXT_MODEL, GEMINI_IMAGE_MODEL, GEMINI_IMAGE_MODEL_PRO
)

# Configuration
BACKEND: Literal["gemini_hybrid", "gemini_native", "gemini_native_pro", "kie"] = os.getenv("ANNOTATION_BACKEND", "gemini_native_pro")

# Google Gemini API Configuration (Official Nano Banana API)
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# KIE.ai Configuration
KIE_JOBS_CREATE = f"{KIE_AI_BASE_URL}/api/v1/jobs/createTask"
KIE_JOBS_RECORD = f"{KIE_AI_BASE_URL}/api/v1/jobs/recordInfo"
KIE_MODEL = "nano-banana-pro"
CATBOX_URL = "https://catbox.moe/user/api.php"


# Analysis prompts
PROFILE_ANALYSIS_PROMPT = """Analyze this LinkedIn profile screenshot as a senior marketing expert.

Return a JSON object with this EXACT structure:
{
  "verdict": "One-sentence summary of the profile's biggest weakness",
  "annotations": [
    {
      "issue": "Short title (3-5 words)",
      "suggestion": "Specific actionable improvement (1-2 sentences)",
      "location": "headline|banner|photo|about|experience|featured|activity"
    }
  ]
}

Identify 4-6 specific issues. Focus on:
- Headline: Is it compelling? Does it have keywords?
- Profile photo: Professional? Good lighting?
- Banner image: Custom or generic?
- About/Bio: Specific achievements? Clear mission?
- Experience: Quantifiable results? Metrics?
- Featured section: Showcasing best work?

Return ONLY valid JSON, no markdown code blocks."""


POST_ANALYSIS_PROMPT = """Analyze this LinkedIn post screenshot as a content strategist.

Return a JSON object with this EXACT structure:
{
  "verdict": "One-sentence summary of the post's biggest weakness",
  "annotations": [
    {
      "issue": "Short title (3-5 words)",
      "suggestion": "Specific actionable improvement (1-2 sentences)",
      "location": "hook|content|structure|cta|hashtags|visual"
    }
  ]
}

Identify 3-5 specific issues. Focus on:
- Hook/Opening: Does it grab attention?
- Content structure: Easy to read? Good whitespace?
- Call-to-action: Clear? Compelling?
- Hashtag usage: Relevant? Right number?
- Engagement potential: Invites comments?

Return ONLY valid JSON, no markdown code blocks."""


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def _image_to_base64(image_path: str) -> str:
    """Convert image to base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _get_mime_type(path: str) -> str:
    """Get MIME type from file extension."""
    ext = os.path.splitext(path)[1].lower()
    return {"png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(ext, "image/png")


# ============================================================================
# GEMINI HYBRID BACKEND (Analysis + PIL Rendering)
# ============================================================================

def _gemini_analyze(image_path: str, content_type: str) -> Dict:
    """Use Gemini 2.5 Flash to analyze the image and return structured JSON."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")
    
    img_b64 = _image_to_base64(image_path)
    prompt = PROFILE_ANALYSIS_PROMPT if content_type == "profile" else POST_ANALYSIS_PROMPT
    
    response = requests.post(
        f"{GEMINI_API_BASE}/{GEMINI_TEXT_MODEL}:generateContent",
        headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
        json={
            "contents": [{
                "parts": [
                    {"inlineData": {"mimeType": _get_mime_type(image_path), "data": img_b64}},
                    {"text": prompt}
                ]
            }]
        },
        timeout=120
    )
    
    if response.status_code != 200:
        err = response.json().get("error", {})
        raise RuntimeError(f"Gemini API error: {err.get('message', response.text)[:300]}")
    
    data = response.json()
    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    
    # Clean JSON
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        if text.startswith("json"):
            text = text[4:].strip()
    
    return json.loads(text)


def _render_annotations(image_path: str, analysis: Dict, output_path: str) -> str:
    """Render annotations on image using PIL."""
    # Load image
    img = Image.open(image_path)
    
    # Add white margin on right for notes
    margin_width = 350
    new_img = Image.new("RGB", (img.width + margin_width, img.height), "white")
    new_img.paste(img, (0, 0))
    
    draw = ImageDraw.Draw(new_img)
    
    # Try to load a nice font, fall back to default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
        font_bold = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except:
        font = ImageFont.load_default()
        font_bold = font
        font_small = font
    
    # Colors
    RED = (220, 53, 69)
    DARK_RED = (180, 30, 50)
    
    # Location to approximate Y positions (relative to image height)
    location_positions = {
        "banner": 0.05,
        "photo": 0.12,
        "headline": 0.18,
        "about": 0.35,
        "featured": 0.45,
        "experience": 0.55,
        "activity": 0.70,
        "hook": 0.15,
        "content": 0.35,
        "structure": 0.50,
        "cta": 0.70,
        "hashtags": 0.85,
        "visual": 0.30,
    }
    
    # Draw verdict at top
    verdict = analysis.get("verdict", "")
    if verdict:
        # Draw verdict box
        box_height = 60
        draw.rectangle([(0, 0), (new_img.width, box_height)], fill=(255, 240, 240))
        draw.rectangle([(0, box_height-3), (new_img.width, box_height)], fill=RED)
        
        # Wrap text
        words = verdict.split()
        lines = []
        current = ""
        for word in words:
            test = current + " " + word if current else word
            if len(test) < 80:
                current = test
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        
        y = 10
        draw.text((15, y), "VERDICT:", font=font_bold, fill=DARK_RED)
        for line in lines[:2]:
            y += 18
            draw.text((15, y), line, font=font, fill=(60, 60, 60))
    
    # Draw annotations
    annotations = analysis.get("annotations", [])
    margin_x = img.width + 20
    
    for i, ann in enumerate(annotations):
        location = ann.get("location", "").lower()
        issue = ann.get("issue", "")
        suggestion = ann.get("suggestion", "")
        
        # Get Y position
        y_ratio = location_positions.get(location, 0.3 + i * 0.12)
        y_pos = int(img.height * y_ratio) + 70  # Offset for verdict box
        
        # Draw circle on main image area
        circle_x = img.width - 80
        circle_y = y_pos
        circle_r = 25
        
        # Draw circle outline
        for offset in range(3):
            draw.ellipse(
                [(circle_x - circle_r - offset, circle_y - circle_r - offset),
                 (circle_x + circle_r + offset, circle_y + circle_r + offset)],
                outline=RED, width=2
            )
        
        # Draw number in circle
        draw.text((circle_x - 6, circle_y - 10), str(i + 1), font=font_bold, fill=RED)
        
        # Draw line to margin
        draw.line([(circle_x + circle_r, circle_y), (margin_x - 5, y_pos)], fill=RED, width=2)
        
        # Draw annotation text in margin
        text_y = y_pos - 20
        
        # Issue title
        draw.text((margin_x, text_y), f"{i+1}. {issue}", font=font_bold, fill=DARK_RED)
        text_y += 22
        
        # Suggestion (wrap text)
        words = suggestion.split()
        lines = []
        current = ""
        for word in words:
            test = current + " " + word if current else word
            if len(test) < 40:
                current = test
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        
        for line in lines[:3]:
            draw.text((margin_x, text_y), line, font=font_small, fill=(80, 80, 80))
            text_y += 16
    
    # Save
    Path(os.path.dirname(output_path)).mkdir(parents=True, exist_ok=True)
    new_img.save(output_path, "PNG")
    
    return output_path


def _gemini_hybrid_annotate(image_path: str, content_type: str, output_path: str) -> str:
    """Hybrid approach: Gemini analysis + PIL rendering."""
    print(f"    Using Gemini Hybrid (analysis + PIL render)...")
    
    # Step 1: Analyze with Gemini
    print(f"    Analyzing with {GEMINI_TEXT_MODEL}...")
    analysis = _gemini_analyze(image_path, content_type)
    print(f"    ✓ Got {len(analysis.get('annotations', []))} annotations")
    
    # Save analysis
    analysis_path = output_path.replace(".png", "_analysis.json")
    with open(analysis_path, "w") as f:
        json.dump(analysis, f, indent=2)
    
    # Step 2: Render annotations
    print(f"    Rendering annotations...")
    result = _render_annotations(image_path, analysis, output_path)
    print(f"    ✓ Saved to: {output_path}")
    
    return result


# ============================================================================
# GEMINI NATIVE BACKEND (Direct image generation)
# ============================================================================

def _gemini_native_annotate(image_path: str, content_type: str, output_path: str, use_pro: bool = False) -> str:
    """
    Use official Gemini Nano Banana API for direct image-to-image annotation.
    
    According to official docs: https://ai.google.dev/gemini-api/docs/image-generation
    - gemini-2.5-flash-image (Nano Banana) - Fast, 1024px
    - gemini-3-pro-image-preview (Nano Banana Pro) - Up to 4K
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")
    
    model = GEMINI_IMAGE_MODEL_PRO if use_pro else GEMINI_IMAGE_MODEL
    print(f"    Using Gemini Nano Banana API ({model})...")
    
    img_b64 = _image_to_base64(image_path)
    mime_type = _get_mime_type(image_path)
    
    # OPTIMIZED PROMPT - Tested for best results with Gemini 3 Pro
    if content_type == "profile":
        prompt = """Add MINIMAL red annotation overlays to this LinkedIn profile screenshot.

PRESERVE the original image exactly - keep it crystal clear and sharp.

ADD ONLY:
• 5 thin red circles (2px stroke) around: headline, photo, banner, about, experience
• Red arrows pointing to brief text notes in the margins
• Small text labels with specific actionable suggestions

ANNOTATIONS TO ADD:
1. Headline → "Craft a stronger, more descriptive headline"
2. Photo → "Use a professional headshot"  
3. Banner → "Update with a relevant banner image"
4. About → "Expand on your mission with specifics"
5. Experience → "Add more detailed achievements here"

Style: Professional, minimal, clean annotations
Quality: Maximum resolution and sharpness - no blur or degradation"""
    else:
        prompt = """Add MINIMAL red annotation overlays to this LinkedIn post screenshot.

PRESERVE the original image exactly - keep it crystal clear and sharp.

ADD ONLY:
• 4-5 thin red circles (2px stroke) around key areas
• Red arrows pointing to brief text notes
• Small text labels with specific actionable suggestions

ANNOTATIONS TO ADD:
1. Hook → "Strengthen the opening line"
2. Structure → "Improve readability with whitespace"
3. Content → "Add more value or story"
4. CTA → "Add a clear call-to-action"
5. Hashtags → "Use 3-5 relevant hashtags"

Style: Professional, minimal, clean annotations
Quality: Maximum resolution and sharpness - no blur or degradation"""
    
    # Official Gemini API format from docs
    payload = {
        "contents": [{
            "parts": [
                {"inlineData": {"mimeType": mime_type, "data": img_b64}},
                {"text": prompt}
            ]
        }],
        "generationConfig": {
            "responseModalities": ["IMAGE"]  # Request only annotated image
        }
    }
    
    # For Pro model, use 2:3 aspect ratio (produces best results for LinkedIn profiles)
    if use_pro:
        # 2:3 works best for tall LinkedIn profile screenshots
        # This produces clear, readable annotations with good proportions
        payload["generationConfig"]["imageConfig"] = {
            "aspectRatio": "2:3"
        }
    
    # Retry logic for rate limits (with longer waits for free tier limits)
    max_retries = 5
    retry_delay = 30  # Start with 30 seconds
    
    for attempt in range(max_retries):
        response = requests.post(
            f"{GEMINI_API_BASE}/{model}:generateContent",
            headers={
                "x-goog-api-key": GEMINI_API_KEY,
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=180  # Image generation can take longer
        )
        
        if response.status_code == 200:
            break  # Success!
        
        if response.status_code == 429:
            if attempt < max_retries - 1:
                # Parse retry delay from error if available
                try:
                    err_data = response.json().get("error", {})
                    details = err_data.get("details", [])
                    for detail in details:
                        if detail.get("@type") == "type.googleapis.com/google.rpc.RetryInfo":
                            retry_delay = int(float(detail.get("retryDelay", "15s").rstrip("s")))
                            retry_delay = max(retry_delay, 15)  # Minimum 15 seconds
                except:
                    pass
                
                print(f"    ⚠️ Rate limit hit, retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                raise RuntimeError("Gemini Nano Banana API rate limit exceeded after retries. Please wait and try again.")
        
        # Other errors
        if response.status_code != 200:
            err = response.json().get("error", {})
            raise RuntimeError(f"Gemini Nano Banana API error: {err.get('message', response.text)[:300]}")
    
    data = response.json()
    candidates = data.get("candidates", [])
    
    if not candidates:
        raise RuntimeError("No candidates in Gemini response")
    
    parts = candidates[0].get("content", {}).get("parts", [])
    
    # Extract image from response (official format)
    for part in parts:
        # Check both possible field names
        if "inlineData" in part:
            img_data_b64 = part["inlineData"].get("data")
            if img_data_b64:
                img_data = base64.b64decode(img_data_b64)
                Path(os.path.dirname(output_path)).mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(img_data)
                print(f"    ✓ Saved annotated image to: {output_path}")
                return output_path
        elif "inline_data" in part:
            img_data_b64 = part["inline_data"].get("data")
            if img_data_b64:
                img_data = base64.b64decode(img_data_b64)
                Path(os.path.dirname(output_path)).mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(img_data)
                print(f"    ✓ Saved annotated image to: {output_path}")
                return output_path
        elif "text" in part:
            print(f"    Note: Also received text: {part['text'][:100]}...")
    
    raise RuntimeError("No image data in Gemini Nano Banana response. Check API response format.")


# ============================================================================
# KIE.AI BACKEND
# ============================================================================

def _upload_to_catbox(image_path: str) -> str:
    """Upload to catbox.moe."""
    with open(image_path, "rb") as f:
        response = requests.post(CATBOX_URL, files={"fileToUpload": f}, data={"reqtype": "fileupload"}, timeout=120)
    response.raise_for_status()
    url = response.text.strip()
    if not url.startswith("https://"):
        raise RuntimeError(f"Catbox upload failed: {url}")
    return url


def _kie_annotate(image_path: str, content_type: str, output_path: str) -> str:
    """Use KIE.ai nano-banana-pro."""
    if not KIE_AI_API_KEY:
        raise RuntimeError("KIE_AI_API_KEY not set")
    
    print(f"    Using KIE.ai ({KIE_MODEL})...")
    
    # Upload
    print(f"    Uploading to catbox.moe...")
    image_url = _upload_to_catbox(image_path)
    
    prompt = f"""As a marketing expert, analyze this LinkedIn {content_type} and add annotations:
- Draw RED BOXES or CIRCLES around weak areas
- Add ARROWS pointing to issues
- Include CLEAR TEXT CALLOUTS with specific suggestions
Make annotations professional, visually clear, and actionable."""
    
    # Create task
    response = requests.post(
        KIE_JOBS_CREATE,
        headers={"Authorization": f"Bearer {KIE_AI_API_KEY}", "Content-Type": "application/json"},
        json={"model": KIE_MODEL, "input": {"prompt": prompt, "image_input": [image_url], "aspect_ratio": "auto", "resolution": "2K", "output_format": "png"}},
        timeout=30
    )
    
    data = response.json()
    if data.get("code") == 402:
        raise RuntimeError("KIE.ai credits insufficient. Top up at https://kie.ai/billing")
    if data.get("code") != 200:
        raise RuntimeError(f"KIE.ai error: {data}")
    
    task_id = data["data"]["taskId"]
    print(f"    Task: {task_id}")
    
    # Poll
    print(f"    Waiting for completion...")
    deadline = time.time() + 180
    while time.time() < deadline:
        response = requests.get(KIE_JOBS_RECORD, params={"taskId": task_id}, headers={"Authorization": f"Bearer {KIE_AI_API_KEY}"}, timeout=30)
        task = response.json().get("data", {})
        if task.get("state") == "success":
            result = json.loads(task.get("resultJson", "{}"))
            result_url = result.get("resultUrls", [None])[0]
            if result_url:
                img_response = requests.get(result_url, timeout=120)
                Path(os.path.dirname(output_path)).mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(img_response.content)
                print(f"    ✓ Saved to: {output_path}")
                return output_path
        elif task.get("state") in ("fail", "failed"):
            raise RuntimeError(f"Task failed: {task.get('failMsg')}")
        time.sleep(5)
    
    raise TimeoutError("KIE.ai task timed out")


# ============================================================================
# MAIN API
# ============================================================================

def annotate_image(image_path: str, content_type: str, output_path: str, backend: Optional[str] = None) -> str:
    """
    Annotate a LinkedIn screenshot using the specified backend.
    
    Backends:
    - gemini_hybrid: Gemini text model for analysis + PIL rendering (FREE)
    - gemini_native: Official Gemini Nano Banana API (gemini-2.5-flash-image)
    - gemini_native_pro: Official Gemini Nano Banana Pro API (gemini-3-pro-image-preview, 4K)
    - kie: KIE.ai nano-banana-pro (paid)
    """
    use_backend = backend or BACKEND
    
    if use_backend == "gemini_hybrid":
        return _gemini_hybrid_annotate(image_path, content_type, output_path)
    elif use_backend == "gemini_native":
        try:
            return _gemini_native_annotate(image_path, content_type, output_path, use_pro=False)
        except RuntimeError as e:
            if any(x in str(e).lower() for x in ["quota", "limit", "rate limit"]):
                print(f"    ⚠️ Quota/Rate limit issues, falling back to gemini_hybrid...")
                return _gemini_hybrid_annotate(image_path, content_type, output_path)
            raise
    elif use_backend == "gemini_native_pro":
        try:
            return _gemini_native_annotate(image_path, content_type, output_path, use_pro=True)
        except RuntimeError as e:
            if any(x in str(e).lower() for x in ["quota", "limit", "rate limit"]):
                print(f"    ⚠️ Quota/Rate limit issues, falling back to gemini_hybrid...")
                return _gemini_hybrid_annotate(image_path, content_type, output_path)
            raise
    else:
        return _kie_annotate(image_path, content_type, output_path)


def annotate_all(profile_dir: str, backend: Optional[str] = None) -> Dict[str, str]:
    """Annotate all screenshots in a profile directory."""
    results: Dict[str, str] = {}
    output_dir = os.path.join(profile_dir, "nano_banana_annotated")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Profile
    profile_src = os.path.join(profile_dir, "screenshot.png")
    if os.path.exists(profile_src):
        print(f"\n  📸 Annotating profile screenshot...")
        try:
            results["profile"] = annotate_image(profile_src, "profile", os.path.join(output_dir, "profile.png"), backend)
        except Exception as e:
            print(f"    ⚠️ Failed: {e}")
    
    # Posts
    posts_dir = os.path.join(profile_dir, "post_screenshots")
    post_paths = sorted(glob.glob(os.path.join(posts_dir, "*.png")))
    
    for idx, post_path in enumerate(post_paths, 1):
        print(f"\n  📸 Annotating post {idx}/{len(post_paths)}...")
        try:
            results[f"post_{idx}"] = annotate_image(post_path, "post", os.path.join(output_dir, f"post_{idx}.png"), backend)
        except Exception as e:
            print(f"    ⚠️ Failed: {e}")
    
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Annotate LinkedIn screenshots using Gemini Nano Banana API or other backends"
    )
    parser.add_argument("profile_dir", help="Path to profile directory")
    parser.add_argument(
        "--backend",
        choices=["gemini_hybrid", "gemini_native", "gemini_native_pro", "kie"],
        default=BACKEND,
        help="Backend: gemini_native (Nano Banana), gemini_native_pro (Nano Banana Pro), gemini_hybrid (free), or kie (paid)"
    )
    parser.add_argument("--profile-only", action="store_true", help="Only annotate profile screenshot")
    args = parser.parse_args()
    
    print(f"\n{'='*60}\nNANO BANANA ANNOTATION (Backend: {args.backend})\n{'='*60}")
    
    if args.profile_only:
        result = annotate_image(
            os.path.join(args.profile_dir, "screenshot.png"),
            "profile",
            os.path.join(args.profile_dir, "nano_banana_annotated", "profile.png"),
            args.backend
        )
        print(f"\n✅ Done: {result}")
    else:
        results = annotate_all(args.profile_dir, args.backend)
        print(f"\n{'='*60}\n✅ Annotated {len(results)} images\n{'='*60}")
