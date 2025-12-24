"""
Editorial Markup Renderer - Minimal, quiet visual markup.

Visual rules (STRICT):
- NO sidebars
- NO paragraphs on image
- NO advice on image
- Colors: neutral gray (#666) + ONE accent (#D32F2F for critical)

Allowed on-image elements:
- Small numbered dot (16px diameter)
- Thin 1-2px outline around evidence
- One editorial caption per evidence (≤12 words)

If it looks like a UX annotation → fail.
"""

import os
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any, List, Tuple, Optional
import math


class ColorScheme:
    """Minimal color palette - like a red pen editor's marks."""
    NEUTRAL = "#555555"      # Dark gray for subtle elements
    ACCENT = "#C41E3A"       # Cardinal red - like a red pen
    MARKER_BG = "#C41E3A"    # Red marker background
    MARKER_TEXT = "#FFFFFF"  # White marker text
    CAPTION_BG = "#1a1a1a"   # Near-black caption background
    CAPTION_BG_ALPHA = 220   # More opaque for readability
    CAPTION_TEXT = "#FFFFFF" # White caption text


class EditorialRenderer:
    """Renders minimal editorial markup on images - like red pen editor marks."""
    
    MARKER_SIZE = 20        # Diameter of numbered dots - slightly larger
    OUTLINE_WIDTH = 2       # Width of evidence outlines
    CAPTION_PADDING = 8     # Padding around captions
    CAPTION_MAX_WORDS = 8   # Max words in caption - keep it punchy
    
    def __init__(self):
        self.fonts = self._load_fonts()
    
    def _load_fonts(self) -> Dict[str, ImageFont.FreeTypeFont]:
        """Load fonts for rendering."""
        fonts = {}
        
        # Try common font paths
        font_paths = [
            "/System/Library/Fonts/SFNSText.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        
        font_loaded = False
        for path in font_paths:
            if os.path.exists(path):
                try:
                    fonts['marker'] = ImageFont.truetype(path, 11)
                    fonts['caption'] = ImageFont.truetype(path, 13)
                    font_loaded = True
                    break
                except Exception:
                    continue
        
        if not font_loaded:
            fonts['marker'] = ImageFont.load_default()
            fonts['caption'] = ImageFont.load_default()
        
        return fonts
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _hex_to_rgba(self, hex_color: str, alpha: int) -> Tuple[int, int, int, int]:
        """Convert hex color to RGBA tuple."""
        rgb = self._hex_to_rgb(hex_color)
        return (*rgb, alpha)
    
    def render(self, image_path: str, evidence: Dict[str, Any], 
               output_path: str, is_critical: bool = True) -> str:
        """
        Render minimal editorial markup on an image.
        
        Args:
            image_path: Path to the clean content image
            evidence: Evidence data from evidence_selector
            output_path: Where to save the annotated image
            is_critical: Whether to use accent color
            
        Returns:
            Path to the rendered image
        """
        # Load image
        img = Image.open(image_path).convert("RGBA")
        
        # Create overlay for semi-transparent elements
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        overlay_draw = ImageDraw.Draw(overlay)
        
        evidence_items = evidence.get("evidence", [])
        
        for item in evidence_items:
            bbox = item.get("bounding_box", {})
            x1, y1 = bbox.get("x1", 0), bbox.get("y1", 0)
            x2, y2 = bbox.get("x2", 0), bbox.get("y2", 0)
            
            if x2 <= x1 or y2 <= y1:
                continue
            
            # Choose color
            color = self._hex_to_rgb(ColorScheme.ACCENT if is_critical else ColorScheme.NEUTRAL)
            
            # 1. Draw thin outline around evidence
            self._draw_outline(draw, (x1, y1, x2, y2), color)
            
            # 2. Draw numbered marker
            marker_id = item.get("id", 1)
            marker_pos = self._calculate_marker_position(x1, y1, x2, y2, img.width, img.height)
            self._draw_marker(draw, marker_pos, marker_id)
            
            # 3. Draw editorial caption (if provided)
            caption = item.get("editorial_caption", "")
            if caption:
                self._draw_caption(img, overlay_draw, caption, (x1, y1, x2, y2))
        
        # Composite overlay
        img = Image.alpha_composite(img, overlay)
        
        # Convert to RGB for saving
        final = Image.new("RGB", img.size, (255, 255, 255))
        final.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save
        final.save(output_path, "PNG", quality=95)
        
        return output_path
    
    def _draw_outline(self, draw: ImageDraw.Draw, bbox: Tuple[int, int, int, int], 
                      color: Tuple[int, int, int]):
        """Draw thin outline around evidence region."""
        x1, y1, x2, y2 = bbox
        
        # Draw rectangle with thin stroke
        for i in range(self.OUTLINE_WIDTH):
            draw.rectangle(
                [x1 - i, y1 - i, x2 + i, y2 + i],
                outline=color,
                width=1
            )
    
    def _calculate_marker_position(self, x1: int, y1: int, x2: int, y2: int,
                                    img_width: int, img_height: int) -> Tuple[int, int]:
        """
        Calculate optimal marker position near the evidence box.
        
        Places marker at top-left corner, offset outside the box.
        """
        offset = 4  # pixels from the box
        marker_x = max(0, x1 - self.MARKER_SIZE - offset)
        marker_y = max(0, y1 - offset)
        
        # If marker would be off-screen left, put it inside
        if marker_x < 0:
            marker_x = x1 + offset
        
        return (marker_x, marker_y)
    
    def _draw_marker(self, draw: ImageDraw.Draw, pos: Tuple[int, int], marker_id: int):
        """Draw small numbered marker dot."""
        x, y = pos
        
        # Draw circle
        draw.ellipse(
            [x, y, x + self.MARKER_SIZE, y + self.MARKER_SIZE],
            fill=self._hex_to_rgb(ColorScheme.MARKER_BG)
        )
        
        # Draw number
        text = str(marker_id)
        text_bbox = draw.textbbox((0, 0), text, font=self.fonts['marker'])
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        text_x = x + (self.MARKER_SIZE - text_width) // 2
        text_y = y + (self.MARKER_SIZE - text_height) // 2 - 1
        
        draw.text(
            (text_x, text_y),
            text,
            fill=self._hex_to_rgb(ColorScheme.MARKER_TEXT),
            font=self.fonts['marker']
        )
    
    def _draw_caption(self, img: Image.Image, overlay_draw: ImageDraw.Draw,
                      caption: str, bbox: Tuple[int, int, int, int]):
        """
        Draw editorial caption - positioned like an editor's margin note.
        
        Tries to place to the right of the box, falls back to below if no space.
        """
        x1, y1, x2, y2 = bbox
        
        # Truncate caption if too long
        words = caption.split()
        if len(words) > self.CAPTION_MAX_WORDS:
            caption = " ".join(words[:self.CAPTION_MAX_WORDS])
        
        # Calculate text dimensions
        text_bbox = overlay_draw.textbbox((0, 0), caption, font=self.fonts['caption'])
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Try to position to the RIGHT of the box (like margin note)
        right_space = img.width - x2 - 20
        
        if right_space >= text_width + self.CAPTION_PADDING * 2:
            # Place to the right
            caption_x = x2 + 15
            caption_y = y1 + 5  # Align with top of box
        else:
            # Fall back to below the box
            caption_x = max(self.CAPTION_PADDING, x1)
            caption_y = min(y2 + 8, img.height - text_height - self.CAPTION_PADDING * 2)
        
        # Draw semi-transparent background pill
        bg_x1 = caption_x - self.CAPTION_PADDING
        bg_y1 = caption_y - 4
        bg_x2 = caption_x + text_width + self.CAPTION_PADDING
        bg_y2 = caption_y + text_height + 4
        
        # Draw rounded rectangle background
        overlay_draw.rounded_rectangle(
            [bg_x1, bg_y1, bg_x2, bg_y2],
            radius=4,
            fill=self._hex_to_rgba(ColorScheme.CAPTION_BG, ColorScheme.CAPTION_BG_ALPHA)
        )
        
        # Draw caption text
        overlay_draw.text(
            (caption_x, caption_y),
            caption,
            fill=(255, 255, 255, 255),
            font=self.fonts['caption']
        )


def render_all_editorial(profile_dir: str, evidence_data: Dict[str, Dict]) -> Dict[str, str]:
    """
    Render editorial markup on all clean content images.
    
    Args:
        profile_dir: Path to the profile output directory
        evidence_data: Dict of evidence from evidence_selector
        
    Returns:
        Dict mapping content type to annotated image path
    """
    renderer = EditorialRenderer()
    clean_dir = os.path.join(profile_dir, "clean_content")
    output_dir = os.path.join(profile_dir, "editorial_teardown")
    os.makedirs(output_dir, exist_ok=True)
    
    results = {}
    
    for content_key, evidence in evidence_data.items():
        # Skip if no valid evidence
        if not evidence.get("is_valid", False) and not evidence.get("evidence", []):
            print(f"  Skipping {content_key} - no valid evidence")
            continue
        
        # Determine paths
        if content_key == "profile":
            input_path = os.path.join(clean_dir, "clean_profile.png")
            output_path = os.path.join(output_dir, "profile_teardown.png")
        else:
            post_num = content_key.replace("post_", "")
            input_path = os.path.join(clean_dir, f"clean_post_{post_num}.png")
            output_path = os.path.join(output_dir, f"post_{post_num}_teardown.png")
        
        if not os.path.exists(input_path):
            print(f"  Skipping {content_key} - image not found")
            continue
        
        print(f"  Rendering {content_key}...")
        rendered_path = renderer.render(input_path, evidence, output_path)
        results[content_key] = rendered_path
        print(f"    ✓ Saved: {rendered_path}")
    
    return results


if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) > 1:
        profile_dir = sys.argv[1]
        
        # Load evidence
        evidence_path = os.path.join(profile_dir, "evidence.json")
        if not os.path.exists(evidence_path):
            print(f"Evidence not found. Run evidence_selector.py first.")
            sys.exit(1)
        
        with open(evidence_path, "r") as f:
            evidence_data = json.load(f)
        
        print(f"Rendering editorial markup for: {profile_dir}")
        results = render_all_editorial(profile_dir, evidence_data)
        print(f"\nRendered {len(results)} images")
    else:
        print("Usage: python editorial_renderer.py <profile_dir>")

