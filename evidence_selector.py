"""
Evidence Selector - OCR + text matching for exact text regions.

Uses pytesseract OCR to get EXACT text coordinates, not vision guessing.
"""

import os
import json
from typing import Dict, Any, List

from ocr_extractor import extract_ocr
from text_matcher import match_text


class EvidenceSelector:
    """Select evidence using OCR coordinates instead of vision boxes."""

    MAX_EVIDENCE = 3
    MIN_EVIDENCE = 1

    def select_evidence(self, image_path: str, verdict: Dict[str, str]) -> Dict[str, Any]:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Get exact text coordinates from OCR
        ocr_elements = extract_ocr(image_path)
        
        # Match verdict text to OCR elements
        matches = match_text(verdict, ocr_elements, max_results=self.MAX_EVIDENCE)

        evidence_items: List[Dict[str, Any]] = []
        for idx, m in enumerate(matches, 1):
            bbox = {
                "x1": m.get("x1", 0),
                "y1": m.get("y1", 0),
                "x2": m.get("x2", 0),
                "y2": m.get("y2", 0),
            }
            # Use a short, punchy caption from the verdict
            verdict_text = verdict.get("one_sentence_verdict", "")
            caption = verdict_text[:35] + "..." if len(verdict_text) > 35 else verdict_text
            
            evidence_items.append({
                "id": idx,
                "why_it_matters": f"Matches: {m.get('matched_source', '')[:50]}",
                "editorial_caption": caption or "Issue here",
                "bounding_box": bbox,
            })

        return {
            "evidence": evidence_items,
            "evidence_strength": "strong" if evidence_items else "weak",
            "verdict_supported": bool(evidence_items),
        }

    def validate_evidence(self, evidence_result: Dict[str, Any], verdict: Dict[str, str] = None) -> bool:
        evidence = evidence_result.get("evidence", [])
        if len(evidence) < self.MIN_EVIDENCE:
            return False
        if evidence_result.get("evidence_strength") == "weak":
            return False
        return True


def select_evidence_for_all(profile_dir: str, diagnoses: Dict[str, Dict]) -> Dict[str, Dict]:
    selector = EvidenceSelector()
    clean_dir = os.path.join(profile_dir, "clean_content")

    results = {}

    for content_key, verdict in diagnoses.items():
        if content_key == "profile":
            image_path = os.path.join(clean_dir, "clean_profile.png")
        else:
            post_num = content_key.replace("post_", "")
            image_path = os.path.join(clean_dir, f"clean_post_{post_num}.png")

        if not os.path.exists(image_path):
            print(f"  Skipping {content_key} - image not found")
            continue

        print(f"  Selecting evidence for {content_key} (OCR-based)...")
        evidence = selector.select_evidence(image_path, verdict)
        is_valid = selector.validate_evidence(evidence, verdict)
        evidence["is_valid"] = is_valid

        results[content_key] = evidence
        print(f"    Found {len(evidence.get('evidence', []))} pieces of evidence (valid: {is_valid})")

    output_path = os.path.join(profile_dir, "evidence.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Saved evidence to: {output_path}")

    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        profile_dir = sys.argv[1]
        diagnoses_path = os.path.join(profile_dir, "diagnoses.json")
        if not os.path.exists(diagnoses_path):
            print("Diagnoses not found. Run narrative_diagnosis.py first.")
            sys.exit(1)
        with open(diagnoses_path, "r") as f:
            diagnoses = json.load(f)
        print(f"Selecting evidence for: {profile_dir}")
        results = select_evidence_for_all(profile_dir, diagnoses)
        print(f"\nSelected evidence for {len(results)} items")
    else:
        print("Usage: python evidence_selector.py <profile_dir>")
