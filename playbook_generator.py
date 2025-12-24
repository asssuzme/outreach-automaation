"""
Playbook Generator - The real value: rewrites and principles.

All intelligence lives OFF the image. This is where the value is.

Required sections:
A. Editorial Verdict (1 sentence from diagnosis)
B. Why This Fails (3 bullets max, blunt)
C. The Fix (ONE direction, not tips)
D. Before → After Rewrite (headline/first line + ONE key paragraph)
E. Reusable Principle
"""

import os
import json
import re
from typing import Dict, Any, Optional, List
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL


# Banned phrases for quality control
BANNED_PHRASES = [
    "consider adding",
    "you might want to",
    "try adding",
    "add a hook",
    "improve engagement",
    "boost your",
    "optimize your",
    "level up",
    "best practice",
    "industry standard",
    "thought leader",
    "value proposition",
    "personal brand",
    "target audience",
]


class PlaybookGenerator:
    """Generates actionable playbooks from editorial diagnoses."""
    
    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API key required")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
    
    def generate(self, verdict: Dict[str, str], evidence: Dict[str, Any],
                 content_type: str = "profile") -> Dict[str, Any]:
        """
        Generate a playbook from diagnosis and evidence.
        
        Args:
            verdict: The verdict from narrative_diagnosis
            evidence: The evidence from evidence_selector
            content_type: "profile" or "post"
            
        Returns:
            Playbook dict with all sections
        """
        ocr_text = verdict.get("ocr_text", "")
        one_sentence_verdict = verdict.get("one_sentence_verdict", "")
        core_gap = verdict.get("core_gap", "")
        primary_story = verdict.get("primary_story", "")
        actual_signal = verdict.get("actual_signal", "")
        consequence = verdict.get("consequence", "")
        
        # Get evidence captions for context
        evidence_items = evidence.get("evidence", [])
        evidence_context = "\n".join([
            f"- {e.get('editorial_caption', e.get('why_it_matters', ''))}"
            for e in evidence_items
        ])
        
        prompt = f"""You are writing an editorial playbook for a LinkedIn {content_type}.

LOCKED VERDICT: "{one_sentence_verdict}"

DIAGNOSIS:
- What they're trying to say: {primary_story}
- What it actually signals: {actual_signal}
- Core gap: {core_gap}
- Consequence: {consequence}

EVIDENCE MARKERS:
{evidence_context}

ORIGINAL CONTENT (for rewrites):
---
{ocr_text[:2000]}
---

Generate a playbook with EXACTLY these sections:

A. EDITORIAL VERDICT
(Copy the one-sentence verdict exactly)

B. WHY THIS FAILS
(Exactly 3 bullets. Each bullet is ONE sentence. Be blunt. Be specific to this content.)

C. THE FIX
(ONE direction. Not multiple tips. Not vague advice. A single, clear direction that addresses the core gap.)
Format: "Shift from [current state] to [desired state]."

D. BEFORE → AFTER
Provide TWO specific rewrites:
1. The headline/first line - show before and after
2. ONE key paragraph or section - show before and after
(Use actual text from the content. Make the rewrite specific and immediately usable.)

E. REUSABLE PRINCIPLE
(One sentence that the person can apply to ALL their content, not just this piece.)
Format: "If someone [action], they should feel [outcome]."

RULES:
- No generic advice ("add more keywords", "be more engaging")
- No LinkedIn jargon ("thought leader", "value proposition", "personal brand")
- Every bullet must be specific to THIS content
- The fix must be ONE direction, not a list
- Rewrites must use actual text from the original

Return as JSON:
{{
    "editorial_verdict": "...",
    "why_it_fails": ["bullet1", "bullet2", "bullet3"],
    "the_fix": "...",
    "before_after": {{
        "headline": {{"before": "...", "after": "..."}},
        "paragraph": {{"before": "...", "after": "..."}}
    }},
    "reusable_principle": "..."
}}

Return raw JSON only, no markdown."""

        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a senior editor who gives blunt, actionable feedback. No hedging. No pleasantries."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.6
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean up response
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result_text = result_text.strip()
        
        try:
            playbook = json.loads(result_text)
            
            # Ensure editorial_verdict is present
            if not playbook.get("editorial_verdict"):
                playbook["editorial_verdict"] = one_sentence_verdict
            
            # Validate and clean
            playbook = self._validate_playbook(playbook)
            
            return playbook
            
        except json.JSONDecodeError:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if json_match:
                try:
                    playbook = json.loads(json_match.group())
                    playbook = self._validate_playbook(playbook)
                    return playbook
                except:
                    pass
            
            # Return minimal structure on failure
            return {
                "editorial_verdict": one_sentence_verdict,
                "why_it_fails": ["Unable to generate detailed analysis"],
                "the_fix": "Regenerate playbook",
                "before_after": {
                    "headline": {"before": "", "after": ""},
                    "paragraph": {"before": "", "after": ""}
                },
                "reusable_principle": "Unable to generate",
                "parse_error": True
            }
    
    def _validate_playbook(self, playbook: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean playbook output."""
        
        # Check for banned phrases
        all_text = json.dumps(playbook).lower()
        found_banned = []
        for phrase in BANNED_PHRASES:
            if phrase in all_text:
                found_banned.append(phrase)
        
        if found_banned:
            playbook["quality_warnings"] = [f"Contains banned phrase: {p}" for p in found_banned]
        
        # Ensure why_it_fails has exactly 3 items
        fails = playbook.get("why_it_fails", [])
        if len(fails) > 3:
            playbook["why_it_fails"] = fails[:3]
        elif len(fails) < 3:
            while len(playbook["why_it_fails"]) < 3:
                playbook["why_it_fails"].append("See above for details")
        
        return playbook
    
    def format_as_text(self, playbook: Dict[str, Any]) -> str:
        """Format playbook as readable text."""
        lines = []
        
        # A. Editorial Verdict
        lines.append("═══════════════════════════════════════════════")
        lines.append("EDITORIAL VERDICT")
        lines.append("═══════════════════════════════════════════════")
        lines.append(f"\n\"{playbook.get('editorial_verdict', 'N/A')}\"\n")
        
        # B. Why This Fails
        lines.append("───────────────────────────────────────────────")
        lines.append("WHY THIS FAILS")
        lines.append("───────────────────────────────────────────────")
        for bullet in playbook.get("why_it_fails", []):
            lines.append(f"• {bullet}")
        lines.append("")
        
        # C. The Fix
        lines.append("───────────────────────────────────────────────")
        lines.append("THE FIX")
        lines.append("───────────────────────────────────────────────")
        lines.append(f"\n{playbook.get('the_fix', 'N/A')}\n")
        
        # D. Before → After
        lines.append("───────────────────────────────────────────────")
        lines.append("BEFORE → AFTER")
        lines.append("───────────────────────────────────────────────")
        
        before_after = playbook.get("before_after", {})
        
        headline = before_after.get("headline", {})
        if headline.get("before"):
            lines.append("\n[HEADLINE]")
            lines.append(f"Before: \"{headline.get('before', '')}\"")
            lines.append(f"After:  \"{headline.get('after', '')}\"")
        
        paragraph = before_after.get("paragraph", {})
        if paragraph.get("before"):
            lines.append("\n[KEY SECTION]")
            lines.append(f"Before: \"{paragraph.get('before', '')}\"")
            lines.append(f"After:  \"{paragraph.get('after', '')}\"")
        lines.append("")
        
        # E. Reusable Principle
        lines.append("───────────────────────────────────────────────")
        lines.append("REUSABLE PRINCIPLE")
        lines.append("───────────────────────────────────────────────")
        lines.append(f"\n\"{playbook.get('reusable_principle', 'N/A')}\"\n")
        
        return "\n".join(lines)


def generate_all_playbooks(profile_dir: str, diagnoses: Dict[str, Dict],
                           evidence_data: Dict[str, Dict]) -> Dict[str, Dict]:
    """
    Generate playbooks for all diagnosed content.
    
    Args:
        profile_dir: Path to the profile output directory
        diagnoses: Dict of diagnoses from narrative_diagnosis
        evidence_data: Dict of evidence from evidence_selector
        
    Returns:
        Dict mapping content type to playbook
    """
    generator = PlaybookGenerator()
    
    results = {}
    
    for content_key, verdict in diagnoses.items():
        evidence = evidence_data.get(content_key, {})
        
        content_type = "profile" if content_key == "profile" else "post"
        
        print(f"  Generating playbook for {content_key}...")
        playbook = generator.generate(verdict, evidence, content_type)
        
        # Add formatted text version
        playbook["formatted_text"] = generator.format_as_text(playbook)
        
        results[content_key] = playbook
        print(f"    ✓ Verdict: {playbook.get('editorial_verdict', 'N/A')[:60]}...")
    
    # Save results
    output_path = os.path.join(profile_dir, "playbooks.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Saved playbooks to: {output_path}")
    
    # Also save formatted text versions
    text_dir = os.path.join(profile_dir, "editorial_teardown")
    os.makedirs(text_dir, exist_ok=True)
    
    for content_key, playbook in results.items():
        if content_key == "profile":
            text_path = os.path.join(text_dir, "profile_playbook.txt")
        else:
            post_num = content_key.replace("post_", "")
            text_path = os.path.join(text_dir, f"post_{post_num}_playbook.txt")
        
        with open(text_path, "w") as f:
            f.write(playbook.get("formatted_text", ""))
        print(f"    Saved: {text_path}")
    
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        profile_dir = sys.argv[1]
        
        # Load diagnoses and evidence
        diagnoses_path = os.path.join(profile_dir, "diagnoses.json")
        evidence_path = os.path.join(profile_dir, "evidence.json")
        
        if not os.path.exists(diagnoses_path):
            print(f"Diagnoses not found. Run narrative_diagnosis.py first.")
            sys.exit(1)
        
        if not os.path.exists(evidence_path):
            print(f"Evidence not found. Run evidence_selector.py first.")
            sys.exit(1)
        
        with open(diagnoses_path, "r") as f:
            diagnoses = json.load(f)
        
        with open(evidence_path, "r") as f:
            evidence_data = json.load(f)
        
        print(f"Generating playbooks for: {profile_dir}")
        results = generate_all_playbooks(profile_dir, diagnoses, evidence_data)
        print(f"\nGenerated {len(results)} playbooks")
    else:
        print("Usage: python playbook_generator.py <profile_dir>")





