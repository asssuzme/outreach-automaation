"""
Generate a visual profile card from LinkedIn scraped data.
"""
import json
import os
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from typing import Dict, Any


def download_image(url: str) -> Image.Image:
    """Download image from URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    except Exception as e:
        print(f"Could not download image: {e}")
        return None


def create_profile_card(profile_data: Dict[str, Any], output_path: str) -> str:
    """
    Create a visual profile card from LinkedIn data.
    
    Args:
        profile_data: Scraped LinkedIn profile data
        output_path: Path to save the generated image
        
    Returns:
        Path to the saved image
    """
    # Card dimensions
    WIDTH = 800
    HEIGHT = 600
    PADDING = 40
    
    # Colors - Professional dark theme
    BG_COLOR = (26, 26, 46)  # Dark navy
    CARD_COLOR = (45, 45, 70)  # Slightly lighter
    ACCENT_COLOR = (0, 119, 181)  # LinkedIn blue
    TEXT_WHITE = (255, 255, 255)
    TEXT_GRAY = (180, 180, 200)
    
    # Create image
    img = Image.new('RGB', (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Draw card background with rounded corners effect
    card_margin = 20
    draw.rounded_rectangle(
        [card_margin, card_margin, WIDTH - card_margin, HEIGHT - card_margin],
        radius=20,
        fill=CARD_COLOR
    )
    
    # Draw accent bar at top
    draw.rectangle([card_margin, card_margin, WIDTH - card_margin, card_margin + 8], fill=ACCENT_COLOR)
    
    # Try to use system fonts
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
        font_medium = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    except:
        try:
            font_large = ImageFont.truetype("Arial.ttf", 32)
            font_medium = ImageFont.truetype("Arial.ttf", 20)
            font_small = ImageFont.truetype("Arial.ttf", 16)
        except:
            font_large = ImageFont.load_default()
            font_medium = font_large
            font_small = font_large
    
    # Handle nested structure from Apify actor
    basic_info = profile_data.get('basic_info', profile_data)
    experiences = profile_data.get('experience', [])
    
    # Extract profile info
    name = basic_info.get('fullname') or basic_info.get('fullName') or basic_info.get('name', 'Unknown')
    headline = basic_info.get('headline', '')
    
    # Handle location (can be dict or string)
    location_data = basic_info.get('location', '')
    if isinstance(location_data, dict):
        location = location_data.get('full', location_data.get('city', ''))
    else:
        location = str(location_data) if location_data else ''
    
    summary = basic_info.get('about') or basic_info.get('summary', '')
    profile_pic_url = basic_info.get('profile_picture_url') or basic_info.get('profilePicture', '')
    connections = basic_info.get('connection_count', basic_info.get('connectionCount', ''))
    followers = basic_info.get('follower_count', basic_info.get('followersCount', ''))
    
    # Get current position from experience
    current_position = ""
    current_company = basic_info.get('current_company', '')
    
    if experiences and len(experiences) > 0:
        first_exp = experiences[0]
        if isinstance(first_exp, dict):
            current_position = first_exp.get('title', '')
            if not current_company:
                current_company = first_exp.get('company', '')
    
    # Y position tracker
    y = 50
    
    # Profile picture (placeholder circle if no image)
    pic_size = 120
    pic_x = PADDING + 20
    pic_y = y + 30
    
    if profile_pic_url:
        profile_img = download_image(profile_pic_url)
        if profile_img:
            # Resize and make circular
            profile_img = profile_img.resize((pic_size, pic_size), Image.Resampling.LANCZOS)
            # Create circular mask
            mask = Image.new('L', (pic_size, pic_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([0, 0, pic_size, pic_size], fill=255)
            # Apply mask
            output = Image.new('RGBA', (pic_size, pic_size), (0, 0, 0, 0))
            output.paste(profile_img, mask=mask)
            img.paste(output, (pic_x, pic_y), output)
        else:
            # Draw placeholder circle
            draw.ellipse([pic_x, pic_y, pic_x + pic_size, pic_y + pic_size], fill=ACCENT_COLOR)
            # Draw initials
            initials = ''.join([n[0].upper() for n in name.split()[:2]])
            try:
                init_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
            except:
                init_font = font_large
            bbox = draw.textbbox((0, 0), initials, font=init_font)
            init_w = bbox[2] - bbox[0]
            init_h = bbox[3] - bbox[1]
            draw.text(
                (pic_x + (pic_size - init_w) // 2, pic_y + (pic_size - init_h) // 2 - 5),
                initials, fill=TEXT_WHITE, font=init_font
            )
    else:
        # Draw placeholder circle with initials
        draw.ellipse([pic_x, pic_y, pic_x + pic_size, pic_y + pic_size], fill=ACCENT_COLOR)
        initials = ''.join([n[0].upper() for n in name.split()[:2]])
        try:
            init_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
        except:
            init_font = font_large
        bbox = draw.textbbox((0, 0), initials, font=init_font)
        init_w = bbox[2] - bbox[0]
        init_h = bbox[3] - bbox[1]
        draw.text(
            (pic_x + (pic_size - init_w) // 2, pic_y + (pic_size - init_h) // 2 - 5),
            initials, fill=TEXT_WHITE, font=init_font
        )
    
    # Text starting position (right of picture)
    text_x = pic_x + pic_size + 30
    text_y = pic_y + 10
    
    # Name
    draw.text((text_x, text_y), name, fill=TEXT_WHITE, font=font_large)
    text_y += 45
    
    # Headline (truncate if too long)
    if headline:
        max_chars = 50
        if len(headline) > max_chars:
            headline = headline[:max_chars-3] + "..."
        draw.text((text_x, text_y), headline, fill=TEXT_GRAY, font=font_medium)
        text_y += 30
    
    # Current position
    if current_position or current_company:
        position_text = f"{current_position}"
        if current_company:
            position_text += f" at {current_company}"
        if len(position_text) > 55:
            position_text = position_text[:52] + "..."
        draw.text((text_x, text_y), position_text, fill=TEXT_GRAY, font=font_small)
        text_y += 25
    
    # Location
    if location:
        draw.text((text_x, text_y), f"📍 {location}", fill=TEXT_GRAY, font=font_small)
    
    # Stats bar
    stats_y = 220
    draw.line([(PADDING + 20, stats_y), (WIDTH - PADDING - 20, stats_y)], fill=(60, 60, 90), width=1)
    stats_y += 20
    
    # Connections and followers
    stats = []
    if connections:
        stats.append(f"{connections} connections")
    if followers:
        stats.append(f"{followers} followers")
    
    if stats:
        stats_text = "  •  ".join(stats)
        draw.text((PADDING + 30, stats_y), stats_text, fill=TEXT_WHITE, font=font_medium)
    
    stats_y += 50
    
    # Summary section
    if summary:
        draw.text((PADDING + 30, stats_y), "About", fill=ACCENT_COLOR, font=font_medium)
        stats_y += 35
        
        # Wrap summary text
        words = summary.split()
        lines = []
        current_line = []
        max_line_width = WIDTH - PADDING * 2 - 60
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font_small)
            if bbox[2] - bbox[0] <= max_line_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        
        # Show first 5 lines max
        for i, line in enumerate(lines[:5]):
            if i == 4 and len(lines) > 5:
                line = line + "..."
            draw.text((PADDING + 30, stats_y), line, fill=TEXT_GRAY, font=font_small)
            stats_y += 22
    
    # LinkedIn branding at bottom
    brand_y = HEIGHT - 50
    draw.text((PADDING + 30, brand_y), "LinkedIn Profile", fill=TEXT_GRAY, font=font_small)
    
    # LinkedIn logo (simple text version)
    draw.text((WIDTH - PADDING - 80, brand_y), "in", fill=ACCENT_COLOR, font=font_large)
    
    # Save image
    img.save(output_path, 'PNG', quality=95)
    return output_path


def generate_from_json_file(json_path: str, output_path: str = None) -> str:
    """
    Generate profile card from a JSON file.
    
    Args:
        json_path: Path to the profile JSON file
        output_path: Optional output path for the image
        
    Returns:
        Path to the generated image
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        profile_data = json.load(f)
    
    if output_path is None:
        base = os.path.splitext(json_path)[0]
        output_path = f"{base}_card.png"
    
    return create_profile_card(profile_data, output_path)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python profile_card.py <profile_data.json> [output.png]")
        sys.exit(1)
    
    json_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = generate_from_json_file(json_path, output_path)
    print(f"Profile card generated: {result}")

