"""
OCR Extractor - get exact text with bounding boxes.

Primary path: pytesseract (word-level boxes) for precise coordinates.
Fallback: raises with guidance if pytesseract/tesseract not available.
"""

import os
from typing import List, Dict, Any

from PIL import Image


class OCRExtractor:
    """Extract text with coordinates from images."""

    def __init__(self):
        # Lazy import pytesseract to allow environment without it.
        try:
            import pytesseract  # type: ignore
        except ImportError as e:
            raise ImportError(
                "pytesseract is required for OCR extraction. "
                "Install with `pip install pytesseract` and ensure Tesseract is installed on the system."
            ) from e

        self.pytesseract = pytesseract

    def extract(self, image_path: str) -> List[Dict[str, Any]]:
        """Return list of OCR elements with bounding boxes.

        Each element:
        {
            "text": str,
            "x1": int, "y1": int, "x2": int, "y2": int,
            "confidence": float
        }
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        img = Image.open(image_path)

        data = self.pytesseract.image_to_data(
            img,
            output_type=self.pytesseract.Output.DICT,
            config="--psm 3"  # Default, works well for block-level text
        )

        results: List[Dict[str, Any]] = []
        n = len(data.get("text", []))
        for i in range(n):
            text = data["text"][i].strip()
            conf = float(data["conf"][i]) if data["conf"][i] not in ("", "-1") else -1.0
            if not text:
                continue

            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            results.append(
                {
                    "text": text,
                    "x1": int(x),
                    "y1": int(y),
                    "x2": int(x + w),
                    "y2": int(y + h),
                    "confidence": conf,
                }
            )

        return results


def extract_ocr(image_path: str) -> List[Dict[str, Any]]:
    """Convenience function."""
    extractor = OCRExtractor()
    return extractor.extract(image_path)


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ocr_extractor.py <image_path>")
        sys.exit(1)

    path = sys.argv[1]
    out = extract_ocr(path)
    print(json.dumps(out[:20], indent=2))  # show first 20 entries





