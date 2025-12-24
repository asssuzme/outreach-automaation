"""
Editorial Engine V3 - Surgical Precision Architecture

Pipeline: Raw Image -> Vision Crop -> Clean Column + Right Margin -> Vision Analysis -> High-Precision Rendering

Key Features:
1. Smart Content Extraction (Pre-Crop) - removes UI noise
2. High-Precision Visual Grounding - 0-1000 normalized coords on cropped image
3. Added right margin for clean annotation placement
4. Surgical annotation rendering with tight circles
"""

import os
import json
import base64
import random
import math
from typing import List, Tuple, Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

RIGHT_MARGIN_WIDTH = 300  # White margin for notes
COORD_SCALE = 1000        # Use 0-1000 for precision


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class CropBounds(BaseModel):
    """Bounding box for content extraction."""
    x1: int = Field(description="Left edge (0-1000)")
    y1: int = Field(description="Top edge (0-1000)")
    x2: int = Field(description="Right edge (0-1000)")
    y2: int = Field(description="Bottom edge (0-1000)")
    
    @field_validator('x1', 'y1', 'x2', 'y2')
    @classmethod
    def validate_bounds(cls, v):
        return max(0, min(1000, v))


class CropResult(BaseModel):
    """Result of content extraction."""
    content_bounds: CropBounds
    content_type: str = Field(description="'profile' or 'post'")
    has_engagement_bar: bool = Field(default=False)


class SurgicalAnnotation(BaseModel):
    """High-precision annotation with exact text targeting."""
    target_text: str = Field(
        description="The EXACT text string being critiqued (copy verbatim)"
    )
    editorial_note: str = Field(
        description="Blunt observation in 8 words or less"
    )
    bbox: List[int] = Field(
        description="Tight bounding box [x1, y1, x2, y2] in 0-1000 coords around the TARGET TEXT"
    )
    
    @field_validator('bbox')
    @classmethod
    def validate_bbox(cls, v):
        if len(v) != 4:
            raise ValueError("bbox must have exactly 4 values [x1, y1, x2, y2]")
        return [max(0, min(1000, x)) for x in v]
    
    @field_validator('editorial_note')
    @classmethod
    def validate_note(cls, v):
        if len(v.split()) > 10:
            return ' '.join(v.split()[:10])
        return v


class EditorialOutput(BaseModel):
    """Complete editorial analysis with surgical precision."""
    verdict: str = Field(description="Punchy 3-6 word headline")
    the_gap: str = Field(description="2 sentences: what they project + why it fails")
    annotations: List[SurgicalAnnotation] = Field(description="Exactly 2 annotations")
    
    @field_validator('verdict')
    @classmethod
    def validate_verdict(cls, v):
        words = v.split()
        if len(words) > 8:
            return ' '.join(words[:8])
        return v
    
    @field_validator('annotations')
    @classmethod
    def validate_annotations(cls, v):
        if len(v) > 2:
            return v[:2]
        return v


# ============================================================================
# VISION CLIENT
# ============================================================================

class VisionClient:
    """Unified OpenAI Vision client."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required")
        self.client = OpenAI(api_key=self.api_key)
        self.model = model or os.getenv("OPENAI_VISION_MODEL", "gpt-4o")
    
    def encode_image(self, image_path: str) -> str:
        """Encode image to base64 data URL."""
        ext = os.path.splitext(image_path)[1].lower()
        media_type = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}.get(ext, 'image/png')
        with open(image_path, 'rb') as f:
            data = base64.standard_b64encode(f.read()).decode('utf-8')
        return f"data:{media_type};base64,{data}"
    
    def encode_pil_image(self, img: Image.Image) -> str:
        """Encode PIL image to base64 data URL."""
        import io
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        data = base64.standard_b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{data}"
    
    def call(self, image_url: str, prompt: str, max_tokens: int = 1024) -> str:
        """Make a vision API call."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url, "detail": "high"}},
                    {"type": "text", "text": prompt}
                ]
            }],
            max_tokens=max_tokens,
            temperature=0.3
        )
        return response.choices[0].message.content


# ============================================================================
# STEP 1: SMART CONTENT EXTRACTION (PRE-CROP)
# ============================================================================

class ContentExtractor:
    """Extracts clean content column from raw screenshots."""
    
    def __init__(self, vision_client: VisionClient):
        self.vision = vision_client
    
    def extract(self, image_path: str) -> Tuple[Image.Image, str]:
        """
        Extract the main content column, removing UI noise.
        
        Returns:
            Tuple of (cropped PIL Image, content_type)
        """
        img = Image.open(image_path).convert("RGB")
        width, height = img.size
        
        image_url = self.vision.encode_image(image_path)
        
        prompt = f"""Analyze this LinkedIn screenshot ({width}x{height} pixels) and identify the MAIN CONTENT COLUMN only.

YOUR TASK:
1. Find the boundaries of the PRIMARY content (profile card OR post content)
2. EXCLUDE all of these:
   - Left navigation sidebar (Home, My Network, Jobs, etc.)
   - Right sidebar (ads, "People you may know", recommendations)
   - Top navigation bar (search, icons)
   - Comment section and comment input box (for posts)
   
3. For POSTS specifically:
   - Include the post author info, post text, and any images
   - Include the engagement bar (likes, comments, reposts counts)
   - STOP at the engagement bar - exclude all comments below it

4. Provide TIGHT bounds that hug the actual content with minimal padding

Return ONLY valid JSON:
{{
    "content_bounds": {{
        "x1": <left edge 0-1000>,
        "y1": <top edge 0-1000>,
        "x2": <right edge 0-1000>,
        "y2": <bottom edge 0-1000>
    }},
    "content_type": "profile" or "post"
}}

COORDINATE SYSTEM: 0-1000 normalized (0=left/top, 1000=right/bottom)
Return raw JSON only, no markdown."""

        response = self.vision.call(image_url, prompt)
        bounds = self._parse_response(response)
        
        # Convert to pixel coordinates
        px_x1 = int(bounds['x1'] / 1000 * width)
        px_y1 = int(bounds['y1'] / 1000 * height)
        px_x2 = int(bounds['x2'] / 1000 * width)
        px_y2 = int(bounds['y2'] / 1000 * height)
        
        # Ensure valid bounds
        px_x1 = max(0, px_x1)
        px_y1 = max(0, px_y1)
        px_x2 = min(width, max(px_x1 + 100, px_x2))
        px_y2 = min(height, max(px_y1 + 100, px_y2))
        
        # Crop the image
        cropped = img.crop((px_x1, px_y1, px_x2, px_y2))
        
        content_type = bounds.get('content_type', 'profile')
        
        return cropped, content_type
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the crop bounds from response."""
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.startswith("```") and not in_block:
                    in_block = True
                    continue
                elif line.startswith("```"):
                    break
                elif in_block:
                    json_lines.append(line)
            text = "\n".join(json_lines)
        
        # Find JSON object
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]
        
        data = json.loads(text)
        return {
            'x1': data.get('content_bounds', {}).get('x1', 50),
            'y1': data.get('content_bounds', {}).get('y1', 50),
            'x2': data.get('content_bounds', {}).get('x2', 700),
            'y2': data.get('content_bounds', {}).get('y2', 950),
            'content_type': data.get('content_type', 'profile')
        }


# ============================================================================
# STEP 2: ADD RIGHT MARGIN
# ============================================================================

def add_right_margin(img: Image.Image, margin_width: int = RIGHT_MARGIN_WIDTH) -> Image.Image:
    """Add white margin to the right of the image for annotations."""
    width, height = img.size
    new_width = width + margin_width
    
    # Create new image with white background
    new_img = Image.new("RGB", (new_width, height), (255, 255, 255))
    new_img.paste(img, (0, 0))
    
    return new_img


# ============================================================================
# STEP 3: HIGH-PRECISION EDITORIAL ANALYSIS
# ============================================================================

class EditorialAnalyzer:
    """Performs surgical editorial analysis with precise coordinates."""
    
    def __init__(self, vision_client: VisionClient):
        self.vision = vision_client
    
    def analyze(self, img: Image.Image, content_type: str) -> EditorialOutput:
        """
        Analyze the clean, cropped image with surgical precision.
        
        Args:
            img: The cropped content image (without margin)
            content_type: 'profile' or 'post'
            
        Returns:
            EditorialOutput with precise annotations
        """
        width, height = img.size
        image_url = self.vision.encode_pil_image(img)
        
        prompt = f"""You are a BRUTAL EXECUTIVE EDITOR. This is a clean-cropped LinkedIn {content_type}.

IMAGE SIZE: {width}x{height} pixels

YOUR TASK - SURGICAL PRECISION:
1. Identify the CORE NARRATIVE this person projects
2. Identify the SINGLE BIGGEST GAP between claim and reality
3. Select EXACTLY 2 text elements that PROVE your verdict
4. For each element, provide the EXACT BOUNDING BOX of the specific text

ANNOTATION RULES (CRITICAL):
- Only annotate TEXT that exists in this image
- The bounding box must TIGHTLY HUG the text you're critiquing
- If critiquing a headline, the box wraps just that headline
- If critiquing a phrase, the box wraps just that phrase
- DO NOT draw boxes around general areas - be SURGICAL

COORDINATE SYSTEM:
- Use 0-1000 normalized coordinates
- x1, y1 = top-left corner of the text
- x2, y2 = bottom-right corner of the text
- Be PRECISE - imagine drawing a tight rectangle around each word/phrase

EDITORIAL NOTE RULES:
- Maximum 8 words
- Blunt observation, NOT advice
- Good: "Generic title, zero punch"
- Bad: "Consider being more specific" (that's advice)

Return ONLY valid JSON:
{{
    "verdict": "3-6 word punchy headline",
    "the_gap": "Two sentences. What they project. Why it fails.",
    "annotations": [
        {{
            "target_text": "Exact text string from the image",
            "editorial_note": "8 words max, blunt",
            "bbox": [x1, y1, x2, y2]
        }},
        {{
            "target_text": "Exact text string from the image", 
            "editorial_note": "8 words max, blunt",
            "bbox": [x1, y1, x2, y2]
        }}
    ]
}}

VERDICT TONE EXAMPLES:
- "Credentials Without Character"
- "Busy Profile, Empty Message"  
- "All Resume, No Story"
- "High Effort, Low Impact"

Return raw JSON only. No markdown, no explanation."""

        response = self.vision.call(image_url, prompt)
        return self._parse_response(response)
    
    def _parse_response(self, response: str) -> EditorialOutput:
        """Parse the editorial analysis response."""
        text = response.strip()
        
        # Remove markdown code blocks
        if text.startswith("```"):
            lines = text.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.startswith("```") and not in_block:
                    in_block = True
                    continue
                elif line.startswith("```"):
                    break
                elif in_block:
                    json_lines.append(line)
            text = "\n".join(json_lines)
        
        # Find JSON
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]
        
        data = json.loads(text)
        
        # Ensure we have exactly 2 annotations
        annotations = data.get('annotations', [])[:2]
        while len(annotations) < 2:
            annotations.append({
                "target_text": "N/A",
                "editorial_note": "No annotation",
                "bbox": [100, 100, 200, 200]
            })
        
        return EditorialOutput(
            verdict=data.get('verdict', 'Analysis Failed'),
            the_gap=data.get('the_gap', 'Unable to analyze.'),
            annotations=[
                SurgicalAnnotation(
                    target_text=a.get('target_text', ''),
                    editorial_note=a.get('editorial_note', ''),
                    bbox=a.get('bbox', [100, 100, 200, 200])
                )
                for a in annotations
            ]
        )


# ============================================================================
# STEP 4: HIGH-PRECISION RENDERING
# ============================================================================

class SurgicalRenderer:
    """Renders precise, editor-style annotations."""
    
    # Colors
    RED = (196, 30, 58)
    DARK_BG = (26, 26, 26)
    WHITE = (255, 255, 255)
    LIGHT_GRAY = (245, 245, 245)
    
    def __init__(self):
        self.fonts = self._load_fonts()
    
    def _load_fonts(self) -> dict:
        """Load fonts for rendering."""
        fonts = {}
        
        handwritten_paths = [
            "/System/Library/Fonts/Supplemental/Marker Felt.ttc",
            "/System/Library/Fonts/Supplemental/Chalkboard.ttc",
            "/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf",
            "/System/Library/Fonts/Noteworthy.ttc",
        ]
        
        bold_paths = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFNSDisplay-Bold.otf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ]
        
        for path in handwritten_paths:
            if os.path.exists(path):
                try:
                    fonts['note'] = ImageFont.truetype(path, 18)
                    fonts['note_small'] = ImageFont.truetype(path, 14)
                    break
                except:
                    continue
        
        for path in bold_paths:
            if os.path.exists(path):
                try:
                    fonts['verdict'] = ImageFont.truetype(path, 26)
                    fonts['number'] = ImageFont.truetype(path, 16)
                    break
                except:
                    continue
        
        if 'note' not in fonts:
            fonts['note'] = ImageFont.load_default()
            fonts['note_small'] = ImageFont.load_default()
        if 'verdict' not in fonts:
            fonts['verdict'] = ImageFont.load_default()
            fonts['number'] = ImageFont.load_default()
        
        return fonts
    
    def render(self, img: Image.Image, analysis: EditorialOutput, 
               content_width: int) -> Image.Image:
        """
        Render surgical annotations on the image.
        
        Args:
            img: Image with right margin already added
            analysis: Editorial analysis with precise coordinates
            content_width: Width of the original content (before margin)
            
        Returns:
            Annotated image
        """
        img = img.convert("RGBA")
        width, height = img.size
        margin_start = content_width
        
        # Create overlay
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Draw verdict box at top
        verdict_height = self._draw_verdict_box(draw, analysis.verdict, width)
        
        # Draw margin background (subtle)
        draw.rectangle(
            [margin_start, verdict_height, width, height],
            fill=(*self.LIGHT_GRAY, 255)
        )
        
        # Draw annotations
        note_y = verdict_height + 40
        
        for i, annotation in enumerate(analysis.annotations):
            if annotation.target_text == "N/A":
                continue
                
            # Convert 0-1000 coords to pixels (relative to content area)
            x1, y1, x2, y2 = annotation.bbox
            px_x1 = int(x1 / 1000 * content_width)
            px_y1 = int(y1 / 1000 * height)
            px_x2 = int(x2 / 1000 * content_width)
            px_y2 = int(y2 / 1000 * height)
            
            # Ensure valid bounds
            px_x1 = max(5, min(content_width - 20, px_x1))
            px_y1 = max(verdict_height + 5, min(height - 20, px_y1))
            px_x2 = max(px_x1 + 20, min(content_width - 5, px_x2))
            px_y2 = max(px_y1 + 10, min(height - 5, px_y2))
            
            # Draw tight circle around text
            self._draw_tight_circle(draw, (px_x1, px_y1, px_x2, px_y2))
            
            # Draw number badge on the circle
            badge_x = px_x2 + 5
            badge_y = px_y1
            self._draw_number_badge(draw, i + 1, (badge_x, badge_y))
            
            # Draw leader line to margin
            line_start = (badge_x + 14, badge_y + 10)
            line_end = (margin_start + 20, note_y + 15)
            self._draw_leader_line(draw, line_start, line_end)
            
            # Draw margin note
            note_y = self._draw_margin_note(
                draw, annotation.editorial_note, 
                margin_start + 30, note_y, width - margin_start - 40
            )
            note_y += 50
        
        # Composite
        result = Image.alpha_composite(img, overlay)
        return result.convert("RGB")
    
    def _draw_verdict_box(self, draw: ImageDraw.Draw, verdict: str, width: int) -> int:
        """Draw verdict banner at top. Returns height."""
        padding = 18
        
        bbox = draw.textbbox((0, 0), verdict.upper(), font=self.fonts['verdict'])
        text_height = bbox[3] - bbox[1]
        box_height = text_height + padding * 2
        
        # Dark banner
        draw.rectangle([0, 0, width, box_height], fill=(*self.DARK_BG, 245))
        
        # Centered text
        text_width = bbox[2] - bbox[0]
        text_x = (width - text_width) // 2
        draw.text((text_x, padding), verdict.upper(), fill=(*self.WHITE, 255), font=self.fonts['verdict'])
        
        return box_height
    
    def _draw_tight_circle(self, draw: ImageDraw.Draw, bbox: Tuple[int, int, int, int]):
        """Draw a tight, slightly wobbly circle around text."""
        x1, y1, x2, y2 = bbox
        
        # Minimal padding for tight fit
        pad = 6
        x1, y1 = x1 - pad, y1 - pad
        x2, y2 = x2 + pad, y2 + pad
        
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        rx = (x2 - x1) / 2
        ry = (y2 - y1) / 2
        
        # Draw 2-3 wobbly passes
        for _ in range(2):
            points = []
            num_points = 40
            for i in range(num_points):
                angle = 2 * math.pi * i / num_points
                wobble = random.uniform(0.97, 1.03)
                jitter_x = random.randint(-2, 2)
                jitter_y = random.randint(-2, 2)
                x = cx + rx * wobble * math.cos(angle) + jitter_x
                y = cy + ry * wobble * math.sin(angle) + jitter_y
                points.append((x, y))
            points.append(points[0])
            draw.line(points, fill=(*self.RED, 255), width=3)
    
    def _draw_number_badge(self, draw: ImageDraw.Draw, number: int, pos: Tuple[int, int]):
        """Draw a small numbered badge."""
        x, y = pos
        r = 12
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(*self.RED, 255))
        draw.text((x - 5, y - 8), str(number), fill=(*self.WHITE, 255), font=self.fonts['number'])
    
    def _draw_leader_line(self, draw: ImageDraw.Draw, 
                          start: Tuple[int, int], end: Tuple[int, int]):
        """Draw a clean leader line with slight wobble."""
        points = []
        steps = 6
        
        for i in range(steps + 1):
            t = i / steps
            x = start[0] + t * (end[0] - start[0])
            y = start[1] + t * (end[1] - start[1])
            # Minimal wobble
            if 0.2 < t < 0.8:
                x += random.randint(-2, 2)
                y += random.randint(-2, 2)
            points.append((int(x), int(y)))
        
        draw.line(points, fill=(*self.RED, 255), width=2)
        
        # Small arrowhead at start
        if len(points) >= 2:
            p0, p1 = points[0], points[1]
            dx = p1[0] - p0[0]
            dy = p1[1] - p0[1]
            length = math.sqrt(dx*dx + dy*dy)
            if length > 0:
                dx, dy = dx/length, dy/length
                arrow_len = 8
                arrow_w = 4
                tip = p0
                left = (int(tip[0] + arrow_len*dx - arrow_w*dy), 
                       int(tip[1] + arrow_len*dy + arrow_w*dx))
                right = (int(tip[0] + arrow_len*dx + arrow_w*dy),
                        int(tip[1] + arrow_len*dy - arrow_w*dx))
                draw.polygon([tip, left, right], fill=(*self.RED, 255))
    
    def _draw_margin_note(self, draw: ImageDraw.Draw, note: str,
                          x: int, y: int, max_width: int) -> int:
        """Draw wrapped note text. Returns y position after note."""
        words = note.split()
        lines = []
        current = []
        
        for word in words:
            test = ' '.join(current + [word])
            bbox = draw.textbbox((0, 0), test, font=self.fonts['note'])
            if bbox[2] - bbox[0] <= max_width:
                current.append(word)
            else:
                if current:
                    lines.append(' '.join(current))
                current = [word]
        if current:
            lines.append(' '.join(current))
        
        for line in lines:
            draw.text((x, y), line, fill=(*self.RED, 255), font=self.fonts['note'])
            y += 24
        
        return y


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def process_image(image_path: str, output_path: str,
                  api_key: Optional[str] = None,
                  model: Optional[str] = None) -> Dict[str, Any]:
    """
    Complete surgical precision pipeline.
    
    Pipeline: Raw Image -> Vision Crop -> Add Margin -> Vision Analysis -> Render
    """
    print(f"\n{'='*60}")
    print("EDITORIAL ENGINE V3 - SURGICAL PRECISION")
    print(f"{'='*60}")
    print(f"Input: {image_path}")
    
    # Initialize
    vision = VisionClient(api_key=api_key, model=model or "gpt-4o")
    extractor = ContentExtractor(vision)
    analyzer = EditorialAnalyzer(vision)
    renderer = SurgicalRenderer()
    
    # Step 1: Smart Content Extraction
    print("\n[1/4] Extracting content column (removing UI noise)...")
    cropped_img, content_type = extractor.extract(image_path)
    content_width, content_height = cropped_img.size
    print(f"  ✓ Cropped to {content_width}x{content_height} ({content_type})")
    
    # Step 2: Add Right Margin
    print("[2/4] Adding annotation margin...")
    img_with_margin = add_right_margin(cropped_img, RIGHT_MARGIN_WIDTH)
    print(f"  ✓ Final canvas: {img_with_margin.size[0]}x{img_with_margin.size[1]}")
    
    # Step 3: High-Precision Editorial Analysis (on cropped image, not margin)
    print("[3/4] Performing surgical analysis...")
    analysis = analyzer.analyze(cropped_img, content_type)
    print(f"  ✓ Verdict: {analysis.verdict}")
    print(f"  ✓ Gap: {analysis.the_gap[:60]}...")
    for i, a in enumerate(analysis.annotations, 1):
        print(f"  ✓ Annotation {i}: \"{a.target_text[:30]}...\" -> {a.editorial_note}")
    
    # Step 4: High-Precision Rendering
    print("[4/4] Rendering surgical annotations...")
    result = renderer.render(img_with_margin, analysis, content_width)
    
    # Save
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    result.save(output_path, "PNG", quality=95)
    print(f"  ✓ Saved to: {output_path}")
    
    return {
        "verdict": analysis.verdict,
        "the_gap": analysis.the_gap,
        "annotations": [
            {
                "target_text": a.target_text,
                "editorial_note": a.editorial_note,
                "bbox": a.bbox
            }
            for a in analysis.annotations
        ],
        "output_path": output_path,
        "content_size": (content_width, content_height)
    }


def process_profile_folder(profile_dir: str,
                           api_key: Optional[str] = None,
                           model: Optional[str] = None,
                           max_posts: int = 3) -> Dict[str, Any]:
    """Process all screenshots in a profile folder."""
    results = {}
    output_dir = os.path.join(profile_dir, "editorial_v3")
    os.makedirs(output_dir, exist_ok=True)
    
    model = model or os.getenv("OPENAI_VISION_MODEL", "gpt-4o")
    
    print(f"\n{'='*60}")
    print("EDITORIAL ENGINE V3 - SURGICAL PRECISION")
    print(f"Model: {model}")
    print(f"Profile: {profile_dir}")
    print(f"{'='*60}")
    
    # Process profile
    profile_path = os.path.join(profile_dir, "screenshot.png")
    if os.path.exists(profile_path):
        print("\n" + "="*50)
        print("📋 PROFILE")
        print("="*50)
        output_path = os.path.join(output_dir, "profile.png")
        try:
            results["profile"] = process_image(profile_path, output_path, api_key, model)
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results["profile"] = {"error": str(e)}
    
    # Process posts
    post_dir = os.path.join(profile_dir, "post_screenshots")
    if os.path.exists(post_dir):
        post_files = sorted([f for f in os.listdir(post_dir) if f.endswith('.png')])[:max_posts]
        
        for i, post_file in enumerate(post_files, 1):
            print(f"\n{'='*50}")
            print(f"📝 POST {i}/{len(post_files)}")
            print("="*50)
            
            input_path = os.path.join(post_dir, post_file)
            output_path = os.path.join(output_dir, f"post_{i}.png")
            
            try:
                results[f"post_{i}"] = process_image(input_path, output_path, api_key, model)
            except Exception as e:
                print(f"  ❌ Error: {e}")
                results[f"post_{i}"] = {"error": str(e)}
    
    # Save summary
    summary_path = os.path.join(output_dir, "summary.json")
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*60}")
    print("✅ COMPLETE")
    print(f"{'='*60}")
    print(f"  📁 Output: {output_dir}")
    print(f"  🖼️  Processed: {len([k for k in results if 'error' not in results.get(k, {})])}")
    
    return results


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Editorial Engine V3 - Surgical Precision")
        print("\nUsage:")
        print("  python editorial_engine.py <image> [output]")
        print("  python editorial_engine.py --folder <profile_dir> [--model gpt-4o]")
        print("\nExamples:")
        print("  python editorial_engine.py screenshot.png result.png")
        print("  python editorial_engine.py --folder output/jainjatin2525")
        print("  python editorial_engine.py --folder output/jainjatin2525 --model gpt-4o")
        sys.exit(1)
    
    # Parse --model
    model = None
    args = sys.argv[1:]
    if "--model" in args:
        idx = args.index("--model")
        if idx + 1 < len(args):
            model = args[idx + 1]
            args = args[:idx] + args[idx+2:]
    
    if args[0] == "--folder":
        if len(args) < 2:
            print("Error: Provide profile folder path")
            sys.exit(1)
        process_profile_folder(args[1], model=model)
    else:
        image_path = args[0]
        output_path = args[1] if len(args) > 1 else "editorial_output.png"
        process_image(image_path, output_path, model=model)
