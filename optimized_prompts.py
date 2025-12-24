"""
Optimized prompts for Gemini Nano Banana image annotation.

These prompts are designed to:
1. Preserve original screenshot quality
2. Only add minimal overlay annotations
3. Keep text sharp and readable
"""

# Best prompt for minimal, clean annotations
MINIMAL_ANNOTATION_PROMPT = """Add MINIMAL red annotation markers to this LinkedIn profile screenshot.

ADD ONLY:
- 5 small red circles (thin outline, 2-3px stroke) around: headline, photo, banner, about, experience
- Thin red arrows pointing to brief text notes in the margins
- Keep annotations clean, minimal, and professional

CRITICAL QUALITY REQUIREMENTS:
- PRESERVE the original image quality - keep it crystal clear and sharp
- DO NOT blur, compress, or degrade the original screenshot
- Only add thin red graphic overlay elements
- Output at highest possible quality"""

# Precise editor-style prompt
EDITOR_STYLE_PROMPT = """PHOTO EDITING TASK: Add annotation layer to this image.

Source: LinkedIn profile screenshot (PRESERVE EXACTLY - do not modify)
Overlay: Add these graphic elements only:
  • Red circle outlines (thin, #E53935, 2px stroke) around 5 areas
  • Red arrows (thin) → text callouts in margins
  • Brief white/black text labels (small font)

Quality requirements:
- Sharpness: Preserve ALL original text and image details
- No compression or quality loss
- The original screenshot must remain pixel-perfect under the annotations
- Output maximum resolution"""

# Professional non-destructive prompt
PROFESSIONAL_PROMPT = """As a professional image editor, add NON-DESTRUCTIVE annotations to this LinkedIn profile.

Your edits must preserve the original:
- Base layer: Original screenshot (LOCKED - do not touch, keep crystal clear)
- Overlay layer: Red annotation graphics ONLY

Annotations to add:
1. Headline → red circle + arrow + "Add value proposition"
2. Photo → red circle + arrow + "Check lighting quality"  
3. Banner → red circle + arrow + "Use custom branding"
4. About → red circle + arrow + "Add metrics & achievements"
5. Experience → red circle + arrow + "Quantify results"

Style: Thin red lines, small text, minimal and clean.
Output the highest quality image possible with zero degradation to original."""

# Function to run annotation with best prompt
def annotate_with_gemini(image_path: str, output_path: str, api_key: str, model: str = "gemini-3-pro-image-preview"):
    """
    Annotate a LinkedIn screenshot using Gemini's image generation.
    
    Args:
        image_path: Path to the screenshot
        output_path: Where to save the annotated image
        api_key: Gemini API key
        model: Model to use (gemini-3-pro-image-preview or nano-banana-pro-preview)
    """
    import requests
    import base64
    from pathlib import Path
    
    # Load image
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
    
    # Use the minimal prompt (best results)
    prompt = MINIMAL_ANNOTATION_PROMPT
    
    payload = {
        "contents": [{
            "parts": [
                {"inlineData": {"mimeType": "image/png", "data": img_b64}},
                {"text": prompt}
            ]
        }],
        "generationConfig": {
            "responseModalities": ["IMAGE"]
        }
    }
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    response = requests.post(url, json=payload, timeout=180)
    
    if response.status_code == 200:
        data = response.json()
        for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
            if "inlineData" in part:
                img_data = base64.b64decode(part["inlineData"]["data"])
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(img_data)
                return output_path
    else:
        error = response.json().get("error", {}).get("message", response.text)
        raise RuntimeError(f"API error: {error}")


if __name__ == "__main__":
    import sys
    from config import GEMINI_API_KEY
    
    if len(sys.argv) < 3:
        print("Usage: python optimized_prompts.py <input_image> <output_image>")
        sys.exit(1)
    
    result = annotate_with_gemini(sys.argv[1], sys.argv[2], GEMINI_API_KEY)
    print(f"✅ Saved: {result}")



