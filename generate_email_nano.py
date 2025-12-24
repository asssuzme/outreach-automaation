"""Generate outreach email using Nano Banana (Gemini) annotated images."""

import base64
import json
import os
from typing import Dict, Any

from config import AGENCY_EMAIL, AGENCY_NAME, AGENCY_WEBSITE


def _image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    ext = os.path.splitext(image_path)[1].lower()
    mime = "image/png" if ext not in [".jpg", ".jpeg"] else "image/jpeg"
    return f"data:{mime};base64,{data}"


def _html_for_image(title: str, image_path: str) -> str:
    if not image_path or not os.path.exists(image_path):
        return ""
    img_b64 = _image_to_base64(image_path)
    return f"""
    <div style="margin-bottom: 32px;">
      <h3 style="font-size: 18px; margin: 0 0 10px 0; color: #111;">{title}</h3>
      <img src="{img_b64}" alt="{title}" style="max-width: 100%; border: 1px solid #ddd; border-radius: 8px;" />
    </div>
    """


def generate_outreach_email(profile_dir: str, annotated_images: Dict[str, str]) -> Dict[str, str]:
    profile_data_path = os.path.join(profile_dir, "profile_data.json")
    with open(profile_data_path, "r") as f:
        profile_data = json.load(f)

    basic_info = profile_data.get("basic_info", {})
    full_name = basic_info.get("fullname", "there")
    first_name = full_name.split()[0] if full_name else "there"

    profile_img = annotated_images.get("profile", "")
    post_keys = sorted([k for k in annotated_images.keys() if k.startswith("post_")], key=lambda x: int(x.split("_")[1]))

    post_sections = ""
    for key in post_keys:
        post_sections += _html_for_image(f"{key.replace('_', ' ').title()} teardown", annotated_images[key])

    profile_section = _html_for_image("Profile teardown", profile_img)

    subject = f"{first_name}, here’s your profile markup"

    body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Profile Teardown</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.7; color: #111; max-width: 760px; margin: 0 auto; padding: 24px; background: #f7f7f7; }}
    .card {{ background: #fff; border-radius: 10px; padding: 28px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }}
    .cta a {{ background: #0077b5; color: #fff; padding: 12px 20px; border-radius: 6px; text-decoration: none; font-weight: 600; }}
  </style>
</head>
<body>
  <div class="card">
    <p style="margin-top: 0;">Hey {first_name},</p>
    <p>I ran your LinkedIn through our visual teardown. Here’s the annotated proof of what’s holding you back and what to fix.</p>

    {profile_section}
    {post_sections}

    <div style="margin-top: 28px; padding: 18px; background: #eef6fb; border-radius: 8px;">
      <p style="margin: 0 0 8px 0; font-weight: 600;">Want this fixed?</p>
      <p style="margin: 0 0 12px 0;">I run {AGENCY_NAME}. We turn profiles into clear, high-conversion personal brands. Zero fluff.</p>
      <p class="cta" style="margin: 0;"><a href="mailto:{AGENCY_EMAIL}?subject=Let's fix my LinkedIn">Reply and let’s tighten this up</a></p>
    </div>

    <p style="color: #666; font-size: 13px; margin-top: 24px;">{AGENCY_NAME} · <a href="{AGENCY_WEBSITE}" style="color: #0077b5; text-decoration: none;">{AGENCY_WEBSITE}</a></p>
  </div>
</body>
</html>
"""

    output_path = os.path.join(profile_dir, "outreach_email_nano.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(body)

    return {"subject": subject, "body": body, "file_path": output_path}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate outreach email using Nano Banana annotated images.")
    parser.add_argument("profile_dir", help="Path to profile directory")
    args = parser.parse_args()

    annotated_dir = os.path.join(args.profile_dir, "nano_banana_annotated")
    annotated_images = {}
    if os.path.exists(annotated_dir):
        for fname in os.listdir(annotated_dir):
            if fname.lower().endswith((".png", ".jpg", ".jpeg")):
                key = os.path.splitext(fname)[0]
                annotated_images[key] = os.path.join(annotated_dir, fname)

    result = generate_outreach_email(args.profile_dir, annotated_images)
    print(f"Email saved to: {result['file_path']}")





