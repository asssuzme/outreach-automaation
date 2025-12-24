"""
Text Matcher - Use GPT to select which OCR elements prove the verdict.

The OCR gives us exact coordinates for text elements.
GPT tells us WHICH text elements support the verdict.
"""

import os
import json
from typing import List, Dict, Any
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL


class TextMatcher:
    """Use LLM to match verdict to specific OCR text elements."""

    def __init__(self, max_results: int = 2):
        self.max_results = max_results
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API key required")
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def match(self, verdict: Dict[str, str], ocr_elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Use GPT to select which OCR elements prove the verdict.
        
        Returns selected OCR elements with their exact coordinates.
        """
        if not ocr_elements:
            return []
        
        # Group OCR elements into lines/sections for better context
        grouped = self._group_ocr_elements(ocr_elements)
        
        # Build prompt
        verdict_text = verdict.get("one_sentence_verdict", "")
        core_gap = verdict.get("core_gap", "")
        
        # Create numbered list of text candidates
        candidates_text = ""
        for i, group in enumerate(grouped[:30], 1):  # Limit to 30 groups
            candidates_text += f"{i}. \"{group['text']}\" (y={group['y1']})\n"
        
        prompt = f"""You are selecting which text elements prove an editorial verdict.

VERDICT: "{verdict_text}"
CORE GAP: {core_gap}

Here are the text elements found in the image (with their vertical position):
{candidates_text}

Select exactly 2 text elements that BEST PROVE the verdict.
Choose elements that demonstrate the problem - headlines, key phrases, or sections that show why the verdict is correct.

Return ONLY valid JSON:
{{"selected": [1, 5]}}

Where the numbers are the element IDs from the list above.
Return raw JSON only, no explanation."""

        try:
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You select text elements that prove editorial verdicts. Return only JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean up response
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            result_text = result_text.strip()
            
            result = json.loads(result_text)
            selected_ids = result.get("selected", [])
            
            # Return the selected OCR groups with their coordinates
            matches = []
            for idx in selected_ids[:self.max_results]:
                if 1 <= idx <= len(grouped):
                    group = grouped[idx - 1]
                    matches.append({
                        "text": group["text"],
                        "x1": group["x1"],
                        "y1": group["y1"],
                        "x2": group["x2"],
                        "y2": group["y2"],
                        "matched_source": f"Element {idx}",
                    })
            
            return matches
            
        except Exception as e:
            print(f"    Warning: Text matching failed: {e}")
            # Fallback: return first 2 elements with reasonable size
            fallback = [e for e in grouped if (e["x2"] - e["x1"]) > 50][:self.max_results]
            return [{
                "text": f["text"],
                "x1": f["x1"],
                "y1": f["y1"],
                "x2": f["x2"],
                "y2": f["y2"],
                "matched_source": "Fallback",
            } for f in fallback]

    def _group_ocr_elements(self, ocr_elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Group nearby OCR words into lines/phrases for better context.
        Filter out obvious UI chrome (nav bars, footers, etc.)
        """
        if not ocr_elements:
            return []
        
        # Filter out elements that are likely UI chrome
        # Skip elements in the top 60px (nav bar) and very small elements
        filtered = [
            e for e in ocr_elements 
            if e.get("y1", 0) > 60  # Skip top nav
            and (e.get("x2", 0) - e.get("x1", 0)) > 20  # Skip tiny elements
            and (e.get("y2", 0) - e.get("y1", 0)) > 8   # Skip very short elements
        ]
        
        if not filtered:
            filtered = ocr_elements  # Fallback if all filtered out
        
        # Sort by y position then x
        sorted_elements = sorted(filtered, key=lambda e: (e.get("y1", 0), e.get("x1", 0)))
        
        groups = []
        current_group = None
        
        for elem in sorted_elements:
            y1 = elem.get("y1", 0)
            
            if current_group is None:
                current_group = {
                    "text": elem.get("text", ""),
                    "x1": elem.get("x1", 0),
                    "y1": elem.get("y1", 0),
                    "x2": elem.get("x2", 0),
                    "y2": elem.get("y2", 0),
                }
            elif abs(y1 - current_group["y1"]) < 15:  # Same line (within 15px)
                # Extend current group
                current_group["text"] += " " + elem.get("text", "")
                current_group["x2"] = max(current_group["x2"], elem.get("x2", 0))
                current_group["y2"] = max(current_group["y2"], elem.get("y2", 0))
            else:
                # New line - save current group and start new
                if current_group["text"].strip():
                    groups.append(current_group)
                current_group = {
                    "text": elem.get("text", ""),
                    "x1": elem.get("x1", 0),
                    "y1": elem.get("y1", 0),
                    "x2": elem.get("x2", 0),
                    "y2": elem.get("y2", 0),
                }
        
        # Don't forget the last group
        if current_group and current_group["text"].strip():
            groups.append(current_group)
        
        return groups


def match_text(verdict: Dict[str, str], ocr_elements: List[Dict[str, Any]], max_results: int = 2) -> List[Dict[str, Any]]:
    matcher = TextMatcher(max_results=max_results)
    return matcher.match(verdict, ocr_elements)


if __name__ == "__main__":
    # Test
    verdict = {
        "one_sentence_verdict": "All credentials, no personality",
        "core_gap": "Lists achievements but no story",
    }
    ocr = [
        {"text": "Mesa", "x1": 10, "y1": 10, "x2": 50, "y2": 30},
        {"text": "School", "x1": 55, "y1": 10, "x2": 100, "y2": 30},
        {"text": "of", "x1": 105, "y1": 10, "x2": 120, "y2": 30},
        {"text": "Business", "x1": 125, "y1": 10, "x2": 200, "y2": 30},
        {"text": "About", "x1": 10, "y1": 50, "x2": 60, "y2": 70},
        {"text": "Young", "x1": 10, "y1": 80, "x2": 50, "y2": 100},
        {"text": "entrepreneur", "x1": 55, "y1": 80, "x2": 150, "y2": 100},
    ]
    print(match_text(verdict, ocr))
