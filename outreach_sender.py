"""
Complete Outreach Sender - LinkedIn + Photos

This module provides multiple methods to send outreach with photos:
1. Direct LinkedIn messaging with Selenium + file upload
2. First connection message with photos (for new connections)
3. Follow-up with images via external link (for InMail limits)

Usage:
    python outreach_sender.py <profile_dir> [--method direct|connection|link]
"""

import os
import sys
import json
import time
import http.server
import socketserver
import threading
import webbrowser
from pathlib import Path
from typing import List, Dict, Optional
import subprocess

# Install packages if needed
def install_packages():
    packages = ['selenium', 'undetected-chromedriver', 'Pillow']
    for pkg in packages:
        try:
            __import__(pkg.replace('-', '_'))
        except ImportError:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '-q'])

install_packages()

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc


class ImageServer:
    """Simple HTTP server to host images temporarily"""
    
    def __init__(self, image_dir: str, port: int = 8765):
        self.image_dir = image_dir
        self.port = port
        self.server = None
        self.thread = None
    
    def start(self):
        """Start the HTTP server in a background thread"""
        os.chdir(self.image_dir)
        handler = http.server.SimpleHTTPRequestHandler
        self.server = socketserver.TCPServer(("", self.port), handler)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        print(f"✓ Image server running at http://localhost:{self.port}/")
        return f"http://localhost:{self.port}"
    
    def stop(self):
        if self.server:
            self.server.shutdown()
            print("✓ Image server stopped")


class LinkedInOutreachSender:
    """Send LinkedIn outreach messages with photos"""
    
    def __init__(self, cookies_file: str = "linkedin_cookies.json"):
        self.cookies_file = cookies_file
        self.driver = None
    
    def load_cookies(self) -> Dict:
        with open(self.cookies_file, 'r') as f:
            return json.load(f)
    
    def start_browser(self):
        options = uc.ChromeOptions()
        options.add_argument('--start-maximized')
        self.driver = uc.Chrome(options=options)
        return self.driver
    
    def login(self) -> bool:
        """Login using cookies"""
        cookies = self.load_cookies()
        self.driver.get("https://www.linkedin.com/login")
        time.sleep(2)
        
        for name, value in cookies.items():
            if name in ['li_at', 'JSESSIONID']:
                self.driver.add_cookie({
                    'name': name, 'value': value,
                    'domain': '.linkedin.com', 'path': '/'
                })
        
        self.driver.get("https://www.linkedin.com/feed/")
        time.sleep(3)
        
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='feed']"))
            )
            print("✓ Logged in successfully")
            return True
        except TimeoutException:
            print("✗ Login failed")
            return False
    
    def send_connection_request_with_note(self, profile_url: str, note: str) -> bool:
        """
        Send a connection request with a personalized note.
        This bypasses the InMail limit but note is limited to 300 chars.
        """
        self.driver.get(profile_url)
        time.sleep(3)
        
        try:
            # Look for Connect button
            connect_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Connect')]"))
            )
            connect_btn.click()
            time.sleep(1)
            
            # Click "Add a note"
            add_note_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Add a note')]"))
            )
            add_note_btn.click()
            time.sleep(1)
            
            # Type the note (max 300 chars)
            note_input = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea.send-invite__custom-message, #custom-message"))
            )
            truncated_note = note[:290] + "..." if len(note) > 300 else note
            note_input.send_keys(truncated_note)
            time.sleep(0.5)
            
            # Send
            send_btn = self.driver.find_element(By.XPATH, "//button[contains(., 'Send invitation') or contains(., 'Send')]")
            send_btn.click()
            time.sleep(2)
            
            print("✓ Connection request with note sent!")
            return True
            
        except TimeoutException:
            print("✗ Could not send connection request")
            return False
    
    def send_direct_message(self, profile_url: str, message: str) -> bool:
        """Send a direct message (for existing connections)"""
        self.driver.get(profile_url)
        time.sleep(3)
        
        try:
            msg_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'Message')]"))
            )
            msg_btn.click()
            time.sleep(2)
            
            # Find and type in message input
            msg_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".msg-form__contenteditable, div[role='textbox']"))
            )
            msg_input.click()
            time.sleep(0.5)
            msg_input.send_keys(message)
            time.sleep(1)
            
            # Send
            send_btn = self.driver.find_element(By.CSS_SELECTOR, "button.msg-form__send-button")
            send_btn.click()
            time.sleep(2)
            
            print("✓ Direct message sent!")
            return True
            
        except TimeoutException:
            print("✗ Could not send direct message")
            return False
    
    def send_inmail_with_file_input(self, profile_url: str, message: str, image_paths: List[str]) -> bool:
        """
        Send InMail with images using Selenium's file input method.
        This attempts to set the file input directly.
        """
        self.driver.get(profile_url)
        time.sleep(3)
        
        try:
            # Click Message button
            msg_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'Message') or contains(., 'Message')]"))
            )
            msg_btn.click()
            time.sleep(2)
            
            # Type message first
            msg_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".msg-form__contenteditable, div[role='textbox'], [contenteditable='true']"))
            )
            msg_input.click()
            time.sleep(0.5)
            msg_input.send_keys(message)
            time.sleep(1)
            
            # Find file input and set files directly
            if image_paths:
                # Find hidden file input
                file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                if file_inputs:
                    # Try to set files on the file input directly
                    for img_path in image_paths:
                        abs_path = os.path.abspath(img_path)
                        try:
                            # Make file input visible temporarily
                            self.driver.execute_script(
                                "arguments[0].style.display = 'block'; arguments[0].style.visibility = 'visible';",
                                file_inputs[0]
                            )
                            file_inputs[0].send_keys(abs_path)
                            time.sleep(1)
                            print(f"✓ Attached: {os.path.basename(img_path)}")
                        except Exception as e:
                            print(f"⚠ Could not attach {img_path}: {e}")
                else:
                    print("⚠ No file input found - sending without images")
            
            # Send message
            send_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.msg-form__send-button, button[type='submit']"))
            )
            send_btn.click()
            time.sleep(2)
            
            print("✓ Message sent!")
            return True
            
        except Exception as e:
            print(f"✗ Error: {e}")
            return False
    
    def close(self):
        if self.driver:
            self.driver.quit()


def generate_outreach_message(profile_dir: str, include_link: bool = False, link_url: str = "") -> tuple:
    """Generate personalized outreach message from teardown data"""
    
    # Load profile data
    profile_path = os.path.join(profile_dir, 'profile_data.json')
    with open(profile_path, 'r') as f:
        profile = json.load(f)
    
    first_name = profile.get('basic_info', {}).get('first_name', 'there')
    profile_url = profile.get('basic_info', {}).get('profile_url', '')
    
    # Load diagnoses
    diag_path = os.path.join(profile_dir, 'diagnoses.json')
    verdict = "Your profile needs work"
    gap = "You're not communicating your value clearly."
    
    if os.path.exists(diag_path):
        with open(diag_path, 'r') as f:
            diag = json.load(f)
        profile_diag = diag.get('profile', {})
        verdict = profile_diag.get('one_sentence_verdict', verdict)
        gap = profile_diag.get('consequence', gap)
    
    # Compose message
    message = f"""Hey {first_name}! 👋

I came across your profile and ran it through my editorial teardown engine. Honest verdict:

"{verdict}"

{gap}

I put together a visual breakdown with specific fixes - I marked exactly where you're losing people."""
    
    if include_link and link_url:
        message += f"\n\n📎 See the full breakdown here: {link_url}"
    else:
        message += "\n\nI've attached the visual proof."
    
    message += """

I run a personal branding agency and we help founders turn "building cool stuff" into content that converts.

Interested in the full playbook?"""
    
    # Get image paths
    teardown_dir = os.path.join(profile_dir, 'editorial_teardown')
    images = []
    if os.path.exists(teardown_dir):
        for f in sorted(os.listdir(teardown_dir)):
            if f.endswith('.png'):
                images.append(os.path.join(teardown_dir, f))
    
    return profile_url, message, images, first_name


def create_image_gallery_html(profile_dir: str, profile_name: str) -> str:
    """Create a simple HTML gallery for the teardown images"""
    
    teardown_dir = os.path.join(profile_dir, 'editorial_teardown')
    images = []
    if os.path.exists(teardown_dir):
        images = sorted([f for f in os.listdir(teardown_dir) if f.endswith('.png')])
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Profile Teardown - {profile_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #1a1a1a;
            color: #fff;
        }}
        h1 {{
            text-align: center;
            margin-bottom: 40px;
        }}
        .gallery {{
            display: grid;
            gap: 30px;
        }}
        .image-card {{
            background: #2a2a2a;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}
        .image-card img {{
            width: 100%;
            display: block;
        }}
        .image-card h3 {{
            padding: 15px 20px;
            margin: 0;
            font-size: 16px;
            color: #ccc;
        }}
        .cta {{
            background: linear-gradient(135deg, #0077b5, #005885);
            padding: 30px;
            border-radius: 12px;
            text-align: center;
            margin-top: 40px;
        }}
        .cta a {{
            background: white;
            color: #0077b5;
            padding: 14px 35px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            display: inline-block;
        }}
    </style>
</head>
<body>
    <h1>📊 Your LinkedIn Profile Teardown</h1>
    
    <div class="gallery">
"""
    
    for img in images:
        title = img.replace('_', ' ').replace('.png', '').title()
        html += f"""
        <div class="image-card">
            <h3>{title}</h3>
            <img src="{img}" alt="{title}">
        </div>
"""
    
    html += """
    </div>
    
    <div class="cta">
        <p style="font-size: 18px; margin-bottom: 20px;">Want to fix these issues? Let's talk strategy.</p>
        <a href="mailto:contact@youragency.com?subject=LinkedIn Profile Help">Get the Full Playbook</a>
    </div>
</body>
</html>
"""
    
    # Save the gallery HTML
    gallery_path = os.path.join(teardown_dir, 'gallery.html')
    with open(gallery_path, 'w') as f:
        f.write(html)
    
    return gallery_path


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Send LinkedIn outreach with photos")
    parser.add_argument("profile_dir", help="Profile directory path")
    parser.add_argument("--method", choices=['direct', 'connection', 'link'], default='direct',
                        help="Method: direct (message with photos), connection (connection request), link (message with image link)")
    parser.add_argument("--port", type=int, default=8765, help="Port for image server (if using link method)")
    args = parser.parse_args()
    
    profile_dir = args.profile_dir
    
    # Generate message and get data
    profile_url, message, images, first_name = generate_outreach_message(profile_dir)
    
    print("\n" + "="*60)
    print("LINKEDIN OUTREACH SENDER")
    print("="*60)
    print(f"Profile: {profile_url}")
    print(f"Method: {args.method}")
    print(f"Images: {len(images)}")
    print("="*60)
    print("\nMESSAGE PREVIEW:")
    print("-"*40)
    print(message)
    print("-"*40)
    
    # Handle different methods
    if args.method == 'link':
        # Create gallery and start server
        teardown_dir = os.path.join(profile_dir, 'editorial_teardown')
        gallery_path = create_image_gallery_html(profile_dir, first_name)
        
        server = ImageServer(teardown_dir, args.port)
        base_url = server.start()
        link_url = f"{base_url}/gallery.html"
        
        # Update message with link
        profile_url, message, _, _ = generate_outreach_message(profile_dir, include_link=True, link_url=link_url)
        
        print(f"\n📎 Gallery URL: {link_url}")
        print("\n⚠️ IMPORTANT: Keep this terminal running to keep the image server active!")
        print("   The recipient needs to view the images while the server is running.")
    
    print(f"\nImages to attach:")
    for img in images:
        print(f"  - {os.path.basename(img)}")
    
    confirm = input("\nType 'SEND' to confirm: ")
    if confirm.upper() != 'SEND':
        print("Cancelled.")
        return
    
    # Send using selected method
    sender = LinkedInOutreachSender()
    
    try:
        sender.start_browser()
        if not sender.login():
            return
        
        if args.method == 'connection':
            # Connection request with note (no images, 300 char limit)
            short_msg = f"Hey {first_name}! Ran your profile through my teardown engine. Found some issues I can help fix. Mind if I send you the full breakdown?"
            sender.send_connection_request_with_note(profile_url, short_msg)
        
        elif args.method == 'link':
            # Message with link to images
            sender.send_direct_message(profile_url, message)
        
        else:  # direct
            # Direct message with photo attachments
            sender.send_inmail_with_file_input(profile_url, message, images)
        
        input("\nPress Enter to close browser...")
        
    finally:
        sender.close()
        if args.method == 'link':
            server.stop()


if __name__ == "__main__":
    main()





