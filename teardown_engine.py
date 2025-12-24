"""
Teardown Engine - Orchestrator with quality checks.

Coordinates the full pipeline:
1. Content Isolation
2. OCR Extraction (within Narrative Diagnosis)
3. Narrative Diagnosis (with quality gate + retries)
4. Evidence Selection
5. Editorial Rendering
6. Playbook Generation

Quality checks:
- Can I summarize the problem in one sentence?
- If user fixes one thing, is it obvious what?
- Does this feel like advice worth paying for?
"""

import os
import json
from typing import Dict, Any, Optional
from datetime import datetime

from content_isolator import isolate_all_content
from narrative_diagnosis import diagnose_all_content
from evidence_selector import select_evidence_for_all
from hand_drawn_renderer import render_hand_drawn
from playbook_generator import generate_all_playbooks


class TeardownEngine:
    """Orchestrates the editorial teardown pipeline."""
    
    def __init__(self, profile_dir: str):
        """
        Initialize the teardown engine.
        
        Args:
            profile_dir: Path to the profile output directory
        """
        self.profile_dir = profile_dir
        self.results = {}
        self.quality_report = {}
    
    def run(self, profile_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Run the full editorial teardown pipeline.
        
        Args:
            profile_data: Optional profile data for additional context
            
        Returns:
            Dict with all pipeline results
        """
        start_time = datetime.now()
        
        print("\n" + "="*60)
        print("EDITORIAL TEARDOWN ENGINE V0")
        print("="*60)
        print(f"Profile: {self.profile_dir}")
        print("="*60 + "\n")
        
        # Step 1: Content Isolation
        print("[1/5] CONTENT ISOLATION")
        print("-"*40)
        clean_content = isolate_all_content(self.profile_dir)
        self.results["clean_content"] = clean_content
        print(f"✓ Isolated {len(clean_content)} content pieces\n")
        
        if not clean_content:
            raise RuntimeError("No content could be isolated. Check screenshots exist.")
        
        # Step 2: Narrative Diagnosis
        print("[2/5] NARRATIVE DIAGNOSIS")
        print("-"*40)
        diagnoses = diagnose_all_content(self.profile_dir, profile_data)
        self.results["diagnoses"] = diagnoses
        print(f"✓ Generated {len(diagnoses)} diagnoses\n")
        
        # Step 3: Evidence Selection
        print("[3/5] EVIDENCE SELECTION")
        print("-"*40)
        evidence = select_evidence_for_all(self.profile_dir, diagnoses)
        self.results["evidence"] = evidence
        print(f"✓ Selected evidence for {len(evidence)} items\n")
        
        # Step 4: Hand-Drawn Rendering
        print("[4/5] HAND-DRAWN RENDERING")
        print("-"*40)
        rendered = self._render_hand_drawn(evidence)
        self.results["rendered"] = rendered
        print(f"✓ Rendered {len(rendered)} teardown images\n")
        
        # Step 5: Playbook Generation
        print("[5/5] PLAYBOOK GENERATION")
        print("-"*40)
        playbooks = generate_all_playbooks(self.profile_dir, diagnoses, evidence)
        self.results["playbooks"] = playbooks
        print(f"✓ Generated {len(playbooks)} playbooks\n")
        
        # Quality Check
        print("="*60)
        print("QUALITY CHECK")
        print("="*60)
        self.quality_report = self._run_quality_checks()
        self._print_quality_report()
        
        # Calculate timing
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Save final results
        self._save_results(duration)
        
        print("\n" + "="*60)
        print(f"COMPLETE in {duration:.1f}s")
        print("="*60 + "\n")
        
        return self.results
    
    def _run_quality_checks(self) -> Dict[str, Any]:
        """
        Run quality checks on the output.
        
        Checks:
        1. Can I summarize the problem in one sentence?
        2. If user fixes one thing, is it obvious what?
        3. Does this feel like advice worth paying for?
        """
        report = {
            "passed": True,
            "checks": [],
            "warnings": [],
            "score": 0
        }
        
        max_score = 0
        current_score = 0
        
        for content_key, diagnosis in self.results.get("diagnoses", {}).items():
            max_score += 3
            
            # Check 1: One-sentence verdict exists and is short
            verdict = diagnosis.get("one_sentence_verdict", "")
            if verdict and len(verdict.split()) <= 20:
                current_score += 1
                report["checks"].append(f"✓ {content_key}: Clear one-sentence verdict")
            else:
                report["warnings"].append(f"⚠ {content_key}: Verdict unclear or too long")
            
            # Check 2: Quality gate passed
            if diagnosis.get("passed_quality_gate", False):
                current_score += 1
                report["checks"].append(f"✓ {content_key}: Passed quality gate")
            else:
                issues = diagnosis.get("quality_issues", [])
                report["warnings"].append(f"⚠ {content_key}: Quality issues: {issues}")
            
            # Check 3: Has playbook with specific fix
            playbook = self.results.get("playbooks", {}).get(content_key, {})
            the_fix = playbook.get("the_fix", "")
            if the_fix and "to" in the_fix.lower():  # Looking for "Shift from X to Y" pattern
                current_score += 1
                report["checks"].append(f"✓ {content_key}: Clear, directional fix")
            else:
                report["warnings"].append(f"⚠ {content_key}: Fix lacks clear direction")
        
        # Calculate final score
        if max_score > 0:
            report["score"] = round((current_score / max_score) * 100)
        
        if report["score"] < 70:
            report["passed"] = False
        
        return report

    def _render_hand_drawn(self, evidence: Dict[str, Dict]) -> Dict[str, str]:
        """Render hand-drawn annotations for all items."""
        output_dir = os.path.join(self.profile_dir, "editorial_teardown")
        os.makedirs(output_dir, exist_ok=True)

        clean_dir = os.path.join(self.profile_dir, "clean_content")
        rendered = {}

        for content_key, ev in evidence.items():
            items = ev.get("evidence", [])
            if not items:
                continue
            if content_key == "profile":
                input_path = os.path.join(clean_dir, "clean_profile.png")
                out_path = os.path.join(output_dir, "profile_teardown.png")
            else:
                post_num = content_key.replace("post_", "")
                input_path = os.path.join(clean_dir, f"clean_post_{post_num}.png")
                out_path = os.path.join(output_dir, f"post_{post_num}_teardown.png")

            if not os.path.exists(input_path):
                continue

            render_hand_drawn(input_path, items, out_path)
            rendered[content_key] = out_path

        return rendered
    
    def _print_quality_report(self):
        """Print quality report to console."""
        print(f"\nQuality Score: {self.quality_report['score']}%")
        print("-"*40)
        
        for check in self.quality_report["checks"]:
            print(f"  {check}")
        
        if self.quality_report["warnings"]:
            print("\nWarnings:")
            for warning in self.quality_report["warnings"]:
                print(f"  {warning}")
        
        status = "PASSED" if self.quality_report["passed"] else "NEEDS REVIEW"
        print(f"\nStatus: {status}")
    
    def _save_results(self, duration: float):
        """Save all results to a summary file."""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "profile_dir": self.profile_dir,
            "content_count": len(self.results.get("clean_content", {})),
            "quality_score": self.quality_report.get("score", 0),
            "quality_passed": self.quality_report.get("passed", False),
            "outputs": {
                "clean_content": self.results.get("clean_content", {}),
                "diagnoses_file": os.path.join(self.profile_dir, "diagnoses.json"),
                "evidence_file": os.path.join(self.profile_dir, "evidence.json"),
                "playbooks_file": os.path.join(self.profile_dir, "playbooks.json"),
                "teardown_images": self.results.get("rendered", {})
            }
        }
        
        output_path = os.path.join(self.profile_dir, "teardown_summary.json")
        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n  Summary saved to: {output_path}")


def run_teardown(profile_dir: str, profile_data: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Convenience function to run the teardown engine.
    
    Args:
        profile_dir: Path to the profile output directory
        profile_data: Optional profile data for additional context
        
    Returns:
        Dict with all pipeline results
    """
    engine = TeardownEngine(profile_dir)
    return engine.run(profile_data)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        profile_dir = sys.argv[1]
        
        # Try to load profile data if available
        profile_data = None
        profile_data_path = os.path.join(profile_dir, "profile_data.json")
        if os.path.exists(profile_data_path):
            with open(profile_data_path, "r") as f:
                profile_data = json.load(f)
        
        results = run_teardown(profile_dir, profile_data)
        
        print("\nOutput files:")
        for key, path in results.get("rendered", {}).items():
            print(f"  {key}: {path}")
        
    else:
        print("Usage: python teardown_engine.py <profile_dir>")
        print("\nExample:")
        print("  python teardown_engine.py output/jainjatin2525")

