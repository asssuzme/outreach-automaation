#!/usr/bin/env python3
"""Test script to regenerate Phase 2 with existing data."""
import sys
import json
from llm_analyzer import analyze_profile_with_llm
from image_annotator import annotate_all_screenshots
from email_generator import generate_outreach_email

def main():
    profile_dir = "output/jainjatin2525"
    
    print("="*60)
    print("TESTING PHASE 2: Humanized Email & Improved Annotations")
    print("="*60 + "\n")
    
    # Step 1: LLM Analysis (if needed, or load existing)
    print("[1/3] Running LLM analysis...")
    try:
        analysis_results = analyze_profile_with_llm(profile_dir)
        print(f"✓ Analysis complete! Profile score: {analysis_results.get('profile_score', 'N/A')}/100\n")
    except Exception as e:
        print(f"Error in analysis: {e}")
        # Try to load existing
        with open(f"{profile_dir}/analysis_results.json", 'r') as f:
            analysis_results = json.load(f)
        print(f"Loaded existing analysis. Profile score: {analysis_results.get('profile_score', 'N/A')}/100\n")
    
    # Step 2: Generate annotated screenshots
    print("[2/3] Generating improved annotated screenshots...")
    try:
        annotated_images = annotate_all_screenshots(profile_dir, analysis_results)
        print(f"✓ Annotated {len(annotated_images)} screenshots")
        for img_type, img_path in annotated_images.items():
            print(f"  - {img_type}: {img_path}")
        print()
    except Exception as e:
        print(f"Error in annotation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Step 3: Generate humanized email
    print("[3/3] Generating humanized email...")
    try:
        email_output = generate_outreach_email(profile_dir, analysis_results, annotated_images)
        print(f"✓ Email generated!")
        print(f"  Subject: {email_output['subject']}")
        print(f"  Saved to: {email_output['file_path']}\n")
    except Exception as e:
        print(f"Error in email generation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("="*60)
    print("SUCCESS! Phase 2 regeneration complete!")
    print("="*60)

if __name__ == "__main__":
    main()





