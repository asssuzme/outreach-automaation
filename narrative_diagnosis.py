"""
Narrative Diagnosis Engine - Text-only verdict engine with quality gates.

This is the MOST IMPORTANT step.

Input: OCR text from the clean image + basic metadata
Output: Verdict JSON with primary_story, actual_signal, core_gap, consequence, one_sentence_verdict

Rules:
- ONE core gap only
- No advice yet
- No politeness
- No tips
"""

import os
import base64
import json
import re
from typing import Dict, Any, Optional, List
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_VISION_MODEL, OPENAI_MODEL


# Banned phrases that indicate weak/generic output
BANNED_PHRASES = [
    "no change needed",
    "looks good",
    "well done",
    "great job",
    "add a hook",
    "improve engagement",
    "consider adding",
    "you might want to",
    "try adding",
    "boost your",
    "optimize your",
    "enhance your",
    "level up",
    "take it to the next level",
    "pro tip",
    "best practice",
    "industry standard",
    "thought leader",
    "value proposition",
]


class NarrativeDiagnosis:
    """Forms editorial verdicts on LinkedIn content."""
    
    MAX_RETRIES = 3
    
    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API key required")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def _extract_text_from_image(self, image_path: str) -> str:
        """Extract text from image using GPT-4 Vision as OCR."""
        base64_image = self._encode_image(image_path)
        
        prompt = """Extract ALL visible text from this LinkedIn screenshot.
        
Return the text exactly as it appears, preserving structure:
- Separate sections with blank lines
- Preserve hierarchy (headings vs body text)
- Include all visible text: names, titles, descriptions, dates, numbers

Return ONLY the extracted text, nothing else."""

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
            max_tokens=2000
        )
        
        return response.choices[0].message.content.strip()
    
    def _check_verdict_quality(self, verdict: Dict[str, str]) -> List[str]:
        """
        Check if verdict passes quality gates.
        
        Returns list of issues (empty = passed).
        """
        issues = []
        
        # Check for banned phrases
        all_text = " ".join(str(v).lower() for v in verdict.values())
        for phrase in BANNED_PHRASES:
            if phrase in all_text:
                issues.append(f"Contains banned phrase: '{phrase}'")
        
        # Check verdict is blunt enough (should be under 20 words)
        verdict_text = verdict.get("one_sentence_verdict", "")
        word_count = len(verdict_text.split())
        if word_count > 25:
            issues.append(f"Verdict too long ({word_count} words, max 25)")
        
        # Check verdict doesn't start with wishy-washy words
        weak_starts = ["this could", "maybe", "perhaps", "it seems", "it appears", "potentially"]
        verdict_lower = verdict_text.lower()
        for weak in weak_starts:
            if verdict_lower.startswith(weak):
                issues.append(f"Verdict starts weak: '{weak}'")
        
        # Check core_gap is specific (not generic)
        core_gap = verdict.get("core_gap", "").lower()
        generic_gaps = ["needs improvement", "could be better", "lacks clarity", "not optimized"]
        for generic in generic_gaps:
            if generic in core_gap:
                issues.append(f"Core gap is generic: '{generic}'")
        
        # Check consequence is real (mentions actual cost)
        consequence = verdict.get("consequence", "").lower()
        if not any(word in consequence for word in ["miss", "lose", "skip", "ignore", "scroll", "forget", "overlook", "pass", "won't", "don't"]):
            issues.append("Consequence doesn't mention a real cost/loss")
        
        return issues
    
    def diagnose(self, image_path: str, content_type: str = "profile", 
                 additional_context: str = "") -> Dict[str, Any]:
        """
        Generate editorial diagnosis for LinkedIn content.
        
        Args:
            image_path: Path to the clean content image
            content_type: "profile" or "post"
            additional_context: Optional additional info (e.g., profile data)
            
        Returns:
            Verdict dict with diagnosis
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Step 1: Extract text (OCR)
        print("    Extracting text from image...")
        ocr_text = self._extract_text_from_image(image_path)
        
        # Step 2: Generate diagnosis (text-only, no image)
        for attempt in range(self.MAX_RETRIES):
            print(f"    Generating diagnosis (attempt {attempt + 1}/{self.MAX_RETRIES})...")
            verdict = self._generate_verdict(ocr_text, content_type, additional_context)
            
            # Step 3: Quality check
            issues = self._check_verdict_quality(verdict)
            
            if not issues:
                verdict["ocr_text"] = ocr_text
                verdict["passed_quality_gate"] = True
                return verdict
            else:
                print(f"    Quality issues: {issues}")
                if attempt < self.MAX_RETRIES - 1:
                    print("    Regenerating...")
        
        # Return last attempt with warning
        verdict["ocr_text"] = ocr_text
        verdict["passed_quality_gate"] = False
        verdict["quality_issues"] = issues
        return verdict
    
    def _generate_verdict(self, ocr_text: str, content_type: str, 
                          additional_context: str) -> Dict[str, str]:
        """Generate the verdict using text-only LLM."""
        
        if content_type == "profile":
            context_desc = "a LinkedIn profile"
            stranger_perspective = "a recruiter, potential client, or industry peer seeing this for the first time"
        else:
            context_desc = "a LinkedIn post"
            stranger_perspective = "someone scrolling their feed who has 2 seconds to decide if this is worth their time"
        
        prompt = f"""You are a brutally honest editorial reviewer. Your job is to diagnose why {context_desc} fails to connect.

Here is the extracted text from the content:

---
{ocr_text}
---

{f"Additional context: {additional_context}" if additional_context else ""}

Your task:
1. Identify what STORY this content is trying to tell
2. Identify what SIGNAL it actually sends to {stranger_perspective}
3. Find the SINGLE BIGGEST GAP between intent and perception
4. Name the REAL COST of this gap (what does the user lose?)
5. Deliver a ONE SENTENCE VERDICT that stings a little

RULES:
- ONE core gap only. If you see multiple issues, pick the most damaging one.
- No advice. No tips. No "consider doing X". Just diagnosis.
- No politeness. Be direct. Be blunt.
- The verdict should feel like something a hiring manager would think but never say.
- Use specific details from the content, not generic observations.

BANNED PHRASES (do not use):
- "No change needed", "looks good", "well done"
- "Add a hook", "improve engagement", "consider adding"
- "Best practice", "thought leader", "value proposition"

Return ONLY valid JSON:
{{
    "primary_story": "What this content is trying to say (be specific)",
    "actual_signal": "What it actually signals to a stranger (be honest)",
    "core_gap": "The single biggest mismatch (one clear statement)",
    "consequence": "What this costs the user - use action words like 'miss', 'lose', 'skip'",
    "one_sentence_verdict": "Blunt verdict under 20 words that would make the user wince"
}}

Examples of good verdicts (tone reference):
- "This reads like a resume, not a person worth following."
- "Strong achievements, but no reason for a stranger to care."
- "Credible, but forgettable."
- "All credentials, zero personality."
- "Tells me what you did, not why it matters."

Return raw JSON only, no markdown."""

        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a brutally honest editorial reviewer. No pleasantries. No hedging. Just truth."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7  # Some creativity for biting verdicts
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean up response
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result_text = result_text.strip()
        
        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            json_match = re.search(r'\{[^{}]*\}', result_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            # Return a default structure
            return {
                "primary_story": "Unable to parse",
                "actual_signal": "Unable to parse",
                "core_gap": "Unable to parse",
                "consequence": "Unable to parse",
                "one_sentence_verdict": "Diagnosis failed - regenerate"
            }


def diagnose_all_content(profile_dir: str, profile_data: Optional[Dict] = None) -> Dict[str, Dict]:
    """
    Run narrative diagnosis on all clean content images.
    
    Args:
        profile_dir: Path to the profile output directory
        profile_data: Optional profile data for additional context
        
    Returns:
        Dict mapping content type to verdict
    """
    engine = NarrativeDiagnosis()
    clean_dir = os.path.join(profile_dir, "clean_content")
    
    if not os.path.exists(clean_dir):
        raise FileNotFoundError(f"Clean content directory not found: {clean_dir}")
    
    results = {}
    
    # Build additional context from profile data
    context = ""
    if profile_data:
        name = profile_data.get("fullName", "")
        headline = profile_data.get("headline", "")
        if name:
            context += f"Name: {name}. "
        if headline:
            context += f"Headline: {headline}. "
    
    # Process profile
    profile_clean = os.path.join(clean_dir, "clean_profile.png")
    if os.path.exists(profile_clean):
        print("  Diagnosing profile...")
        verdict = engine.diagnose(profile_clean, "profile", context)
        results["profile"] = verdict
        print(f"    Verdict: {verdict.get('one_sentence_verdict', 'N/A')}")
    
    # Process posts
    post_files = sorted([f for f in os.listdir(clean_dir) 
                         if f.startswith("clean_post_") and f.endswith(".png")])
    
    for post_file in post_files:
        post_num = post_file.replace("clean_post_", "").replace(".png", "")
        post_path = os.path.join(clean_dir, post_file)
        print(f"  Diagnosing post {post_num}...")
        verdict = engine.diagnose(post_path, "post", context)
        results[f"post_{post_num}"] = verdict
        print(f"    Verdict: {verdict.get('one_sentence_verdict', 'N/A')}")
    
    # Save results
    output_path = os.path.join(profile_dir, "diagnoses.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Saved diagnoses to: {output_path}")
    
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        profile_dir = sys.argv[1]
        print(f"Running narrative diagnosis on: {profile_dir}")
        results = diagnose_all_content(profile_dir)
        print(f"\nDiagnosed {len(results)} items")
    else:
        print("Usage: python narrative_diagnosis.py <profile_dir>")





