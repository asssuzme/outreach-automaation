"""
LinkedIn Messenger with Photo Support

Uses browser automation + pyautogui to handle native file dialogs.
This is the proper way to send photos via LinkedIn messages.
"""

import os
import sys
import time
import json
import subprocess
from pathlib import Path
from typing import List, Optional

# Check for required packages
try:
    import pyautogui
except ImportError:
    print("Installing pyautogui...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyautogui"])
    import pyautogui

try:
    from PIL import Image
    import pyperclip
except ImportError:
    print("Installing required packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "pyperclip"])
    from PIL import Image
    import pyperclip


def copy_image_to_clipboard(image_path: str):
    """
    Copy an image to the system clipboard (macOS).
    
    Args:
        image_path: Path to the image file
    """
    # Convert to absolute path
    abs_path = os.path.abspath(image_path)
    
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Image not found: {abs_path}")
    
    # Use osascript to copy image to clipboard on macOS
    script = f'''
    set theFile to POSIX file "{abs_path}"
    set theImage to read theFile as JPEG picture
    set the clipboard to theImage
    '''
    
    # Try PNG first, fall back to JPEG
    try:
        script_png = f'''
        set the clipboard to (read (POSIX file "{abs_path}") as «class PNGf»)
        '''
        subprocess.run(['osascript', '-e', script_png], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        # Fall back to JPEG
        subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
    
    print(f"  ✓ Copied to clipboard: {os.path.basename(abs_path)}")


def send_linkedin_message_with_photos(
    message: str,
    image_paths: List[str],
    profile_name: str = "Unknown",
    wait_after_paste: float = 2.0
):
    """
    Send a LinkedIn message with photos by pasting from clipboard.
    
    This function assumes:
    1. Browser is already open on LinkedIn
    2. Message dialog is already open
    3. Cursor is in the message input field
    
    Args:
        message: The text message to send
        image_paths: List of image paths to attach
        profile_name: Name for logging
        wait_after_paste: Seconds to wait after each paste
    """
    print(f"\n{'='*60}")
    print("LINKEDIN MESSENGER WITH PHOTOS")
    print(f"{'='*60}")
    print(f"Target: {profile_name}")
    print(f"Message: {len(message)} characters")
    print(f"Photos: {len(image_paths)}")
    print(f"{'='*60}\n")
    
    # First, paste each image
    for i, img_path in enumerate(image_paths):
        print(f"[{i+1}/{len(image_paths)}] Attaching: {os.path.basename(img_path)}")
        
        try:
            # Copy image to clipboard
            copy_image_to_clipboard(img_path)
            time.sleep(0.5)
            
            # Paste with Cmd+V (macOS)
            pyautogui.hotkey('command', 'v')
            print(f"  ✓ Pasted image")
            
            # Wait for upload
            time.sleep(wait_after_paste)
            
        except Exception as e:
            print(f"  ⚠️ Error: {e}")
            continue
    
    # Type the message
    print("\n[+] Typing message...")
    
    # Copy message to clipboard and paste (more reliable than typing)
    pyperclip.copy(message)
    time.sleep(0.3)
    pyautogui.hotkey('command', 'v')
    print("  ✓ Message pasted")
    
    time.sleep(1)
    
    print("\n✅ Ready! Press Cmd+Enter or click Send to deliver.")
    print("   (Script won't auto-send to prevent accidental sends)")


def get_teardown_images(profile_dir: str) -> List[str]:
    """
    Get all editorial teardown images from a profile directory.
    
    Args:
        profile_dir: Path to profile output directory
        
    Returns:
        List of image paths
    """
    teardown_dir = os.path.join(profile_dir, 'editorial_teardown')
    
    if not os.path.exists(teardown_dir):
        print(f"⚠️ No editorial_teardown directory found in {profile_dir}")
        return []
    
    images = []
    
    # Get profile teardown first
    profile_img = os.path.join(teardown_dir, 'profile_teardown.png')
    if os.path.exists(profile_img):
        images.append(profile_img)
    
    # Get post teardowns (sorted)
    post_imgs = sorted([
        os.path.join(teardown_dir, f) 
        for f in os.listdir(teardown_dir) 
        if f.startswith('post_') and f.endswith('_teardown.png')
    ])
    images.extend(post_imgs)
    
    return images


def generate_message_with_photos(profile_dir: str) -> tuple:
    """
    Generate a message and get photo paths for a profile.
    
    Args:
        profile_dir: Path to profile output directory
        
    Returns:
        Tuple of (message, image_paths)
    """
    # Load profile data
    profile_path = os.path.join(profile_dir, 'profile_data.json')
    with open(profile_path, 'r') as f:
        profile_data = json.load(f)
    
    first_name = profile_data.get('basic_info', {}).get('first_name', 'there')
    
    # Load editorial summary if available
    summary_path = os.path.join(profile_dir, 'editorial_v3', 'summary.json')
    verdict = "needs work"
    gap = ""
    
    if os.path.exists(summary_path):
        with open(summary_path, 'r') as f:
            summary = json.load(f)
            verdict = summary.get('profile', {}).get('verdict', verdict)
            gap = summary.get('profile', {}).get('the_gap', gap)
    
    # Also check diagnoses.json as fallback
    diag_path = os.path.join(profile_dir, 'diagnoses.json')
    if os.path.exists(diag_path) and not gap:
        with open(diag_path, 'r') as f:
            diagnoses = json.load(f)
            profile_diag = diagnoses.get('profile', {})
            verdict = profile_diag.get('one_sentence_verdict', verdict)
            gap = profile_diag.get('core_gap', gap)
    
    # Generate message
    message = f"""Hey {first_name}! 👋

I ran your profile through my editorial teardown engine. Honest verdict:

"{verdict}"

{gap}

Check out the visual breakdown I've attached - I marked exactly where you're losing people and how to fix it.

I run a personal branding agency that helps founders like you turn "building cool stuff" into content that actually converts. Want the full playbook?"""
    
    # Get images
    images = get_teardown_images(profile_dir)
    
    return message, images


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python linkedin_messenger.py <profile_dir>")
        print("\nExample:")
        print("  python linkedin_messenger.py output/ashutosh-lath-3a374b2b3")
        print("\nThis script will:")
        print("  1. Load the teardown images from the profile directory")
        print("  2. Generate a personalized message")
        print("  3. Copy/paste images and message to the active LinkedIn message dialog")
        print("\n⚠️  IMPORTANT: Open LinkedIn message dialog FIRST, then run this script!")
        sys.exit(1)
    
    profile_dir = sys.argv[1]
    
    if not os.path.exists(profile_dir):
        print(f"❌ Profile directory not found: {profile_dir}")
        sys.exit(1)
    
    # Generate message and get images
    message, images = generate_message_with_photos(profile_dir)
    
    print("\n" + "="*60)
    print("MESSAGE PREVIEW")
    print("="*60)
    print(message)
    print("="*60)
    print(f"\n📎 Images to attach ({len(images)}):")
    for img in images:
        print(f"   - {os.path.basename(img)}")
    
    print("\n" + "="*60)
    print("INSTRUCTIONS")
    print("="*60)
    print("1. Open LinkedIn in your browser")
    print("2. Navigate to the target profile")
    print("3. Click 'Message' to open the chat dialog")
    print("4. Click inside the message input field")
    print("5. Come back here and press ENTER to start")
    print("="*60)
    
    input("\n👉 Press ENTER when LinkedIn message dialog is ready...")
    
    # Give user time to switch back to browser
    print("\nStarting in 3 seconds... (switch to browser now!)")
    time.sleep(3)
    
    # Get profile name for logging
    try:
        with open(os.path.join(profile_dir, 'profile_data.json'), 'r') as f:
            profile_name = json.load(f).get('basic_info', {}).get('fullname', 'Unknown')
    except:
        profile_name = "Unknown"
    
    # Send the message with photos
    send_linkedin_message_with_photos(
        message=message,
        image_paths=images[:3],  # Limit to 3 images to keep message reasonable
        profile_name=profile_name
    )


if __name__ == "__main__":
    main()





