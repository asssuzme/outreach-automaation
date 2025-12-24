"""
Hand-Drawn Renderer - draw annotations like a red-pen editor.

Visual elements:
- Wobbly circles around text
- Scribbled arrows to margin notes
- Margin note text (short)
- Wavy underlines

Input evidence items:
{
  "id": int,
  "editorial_caption": str,
  "bounding_box": {"x1": int, "y1": int, "x2": int, "y2": int}
}
"""

import os
import random
from typing import Dict, Any, List, Tuple

from PIL import Image, ImageDraw, ImageFont


class HandDrawnRenderer:
    """Render hand-drawn style annotations."""

    RED = (196, 30, 58)  # Cardinal red
    BLACK = (26, 26, 26)
    WHITE = (255, 255, 255)

    def __init__(self):
        self.font = self._load_font()

    def _load_font(self) -> ImageFont.FreeTypeFont:
        paths = [
            "/System/Library/Fonts/Supplemental/Chalkboard.ttc",
            "/System/Library/Fonts/Supplemental/Comic Sans MS.ttf",
            "/System/Library/Fonts/SFNSText.ttf",
        ]
        for p in paths:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, 16)
                except Exception:
                    continue
        return ImageFont.load_default()

    # Drawing helpers -------------------------------------------------
    def _wobble(self, value: int, delta: int = 3) -> int:
        return value + random.randint(-delta, delta)

    def _draw_wobbly_circle(self, draw: ImageDraw.Draw, bbox: Tuple[int, int, int, int]):
        x1, y1, x2, y2 = bbox
        for _ in range(4):
            jitter = 3
            draw.rectangle(
                [
                    self._wobble(x1, jitter),
                    self._wobble(y1, jitter),
                    self._wobble(x2, jitter),
                    self._wobble(y2, jitter),
                ],
                outline=self.RED,
                width=2,
            )

    def _draw_wavy_underline(self, draw: ImageDraw.Draw, bbox: Tuple[int, int, int, int]):
        x1, y1, x2, y2 = bbox
        y = y2 + 4
        step = 6
        points = []
        direction = 1
        for x in range(x1, x2, step):
            points.append((x, y + direction * 3))
            direction *= -1
        if points:
            draw.line(points, fill=self.RED, width=2)

    def _draw_scribble_arrow(self, draw: ImageDraw.Draw, start: Tuple[int, int], end: Tuple[int, int]):
        # Scribbly polyline
        points = []
        steps = 5
        for i in range(steps + 1):
            t = i / steps
            x = int(start[0] + t * (end[0] - start[0]) + random.randint(-3, 3))
            y = int(start[1] + t * (end[1] - start[1]) + random.randint(-3, 3))
            points.append((x, y))
        draw.line(points, fill=self.RED, width=2)
        # Arrowhead
        if len(points) >= 2:
            p1, p2 = points[-2], points[-1]
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            ah1 = (p2[0] - dy // 2 - 4, p2[1] + dx // 2)
            ah2 = (p2[0] + dy // 2 + 4, p2[1] - dx // 2)
            draw.polygon([p2, ah1, ah2], fill=self.RED)

    def _draw_margin_note(self, draw: ImageDraw.Draw, text: str, anchor: Tuple[int, int]):
        x, y = anchor
        draw.text((x, y), text, fill=self.BLACK, font=self.font)

    # Public API ------------------------------------------------------
    def render(self, image_path: str, evidence: List[Dict[str, Any]], output_path: str) -> str:
        img = Image.open(image_path).convert("RGBA")
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        for item in evidence:
            bbox_dict = item.get("bounding_box", {})
            x1, y1 = bbox_dict.get("x1", 0), bbox_dict.get("y1", 0)
            x2, y2 = bbox_dict.get("x2", 0), bbox_dict.get("y2", 0)
            if x2 <= x1 or y2 <= y1:
                continue
            caption = item.get("editorial_caption", "")

            # Wobbly circle around text
            self._draw_wobbly_circle(draw, (x1, y1, x2, y2))

            # Wavy underline
            self._draw_wavy_underline(draw, (x1, y1, x2, y2))

            # Margin note to the right if room, else above
            note_x = min(img.width - 150, x2 + 20)
            note_y = max(10, y1 - 10)
            self._draw_margin_note(draw, caption, (note_x, note_y))

            # Scribbled arrow from note to box
            self._draw_scribble_arrow(draw, (note_x - 10, note_y + 8), (x2, y1))

        # Composite
        result = Image.alpha_composite(img, overlay)
        final = Image.new("RGB", img.size, (255, 255, 255))
        final.paste(result, mask=result.split()[3])

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        final.save(output_path, "PNG", quality=95)
        return output_path


def render_hand_drawn(image_path: str, evidence: List[Dict[str, Any]], output_path: str) -> str:
    renderer = HandDrawnRenderer()
    return renderer.render(image_path, evidence, output_path)


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 3:
        print("Usage: python hand_drawn_renderer.py <image_path> <evidence_json>")
        sys.exit(1)

    img_path = sys.argv[1]
    with open(sys.argv[2], "r") as f:
        ev = json.load(f)

    out_path = "hand_drawn_preview.png"
    render_hand_drawn(img_path, ev, out_path)
    print(f"Saved {out_path}")





