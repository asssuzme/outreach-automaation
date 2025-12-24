"""
LinkedIn Message Sender with Photo Support

Uses Selenium + pyautogui to handle native file dialogs.
This script sends LinkedIn messages WITH photos attached.
"""

import os
import sys
import time
import json
import subprocess
from pathlib import Path

# Install required packages
def install_packages():
    packages = ['selenium', 'pyautogui', 'undetected-chromedriver', 'Pillow']
    for pkg in packages:
        try:
            __import__(pkg.replace('-', '_'))
        except ImportError:
            print(f"Installing {pkg}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '-q'])

install_packages()

import pyautogui
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc


class LinkedInPhotoMessenger:
    def __init__(self, cookies_file: str = "linkedin_cookies.json"):
        self.cookies_file = cookies_file
        self.driver = None
        
    def load_cookies(self):
        """Load LinkedIn cookies from file"""
        if not os.path.exists(self.cookies_file):
            raise FileNotFoundError(f"Cookies file not found: {self.cookies_file}")
        with open(self.cookies_file, 'r') as f:
            return json.load(f)
    
    def start_browser(self):
        """Start Chrome browser with undetected_chromedriver"""
        options = uc.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        self.driver = uc.Chrome(options=options)
        return self.driver
    
    def login_with_cookies(self):
        """Login to LinkedIn using cookies"""
        cookies = self.load_cookies()
        
        # First, go to LinkedIn to set the domain
        self.driver.get("https://www.linkedin.com/login")
        time.sleep(2)
        
        # Add cookies
        for name, value in cookies.items():
            if name in ['li_at', 'JSESSIONID']:
                try:
                    self.driver.add_cookie({
                        'name': name,
                        'value': value,
                        'domain': '.linkedin.com',
                        'path': '/'
                    })
                except Exception as e:
                    print(f"Warning: Could not add cookie {name}: {e}")
        
        # Refresh to apply cookies
        self.driver.get("https://www.linkedin.com/feed/")
        time.sleep(3)
        
        # Verify login
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='feed']"))
            )
            print("✓ Successfully logged in to LinkedIn")
            return True
        except TimeoutException:
            print("✗ Login failed - cookies may be expired")
            return False
    
    def open_profile_message(self, profile_url: str):
        """Navigate to profile and open message dialog"""
        self.driver.get(profile_url)
        time.sleep(3)
        
        # Find and click the Message button
        try:
            message_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'Message') or contains(., 'Message')]"))
            )
            message_btn.click()
            time.sleep(2)
            print("✓ Opened message dialog")
            return True
        except TimeoutException:
            print("✗ Could not find Message button")
            return False
    
    def type_message(self, message: str):
        """Type a message in the message input"""
        try:
            # Find the message input - could be contenteditable or textarea
            msg_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    ".msg-form__contenteditable, [data-artdeco-is-focused], [role='textbox'][contenteditable='true']"
                ))
            )
            msg_input.click()
            time.sleep(0.5)
            
            # Type character by character for contenteditable
            msg_input.send_keys(message)
            time.sleep(1)
            print("✓ Typed message")
            return True
        except TimeoutException:
            print("✗ Could not find message input")
            return False
    
    def attach_photo_with_pyautogui(self, image_path: str):
        """
        Attach a photo using pyautogui to handle native file dialog.
        This is the key method that PhantomBuster and similar tools use.
        """
        # Make image path absolute
        image_path = os.path.abspath(image_path)
        if not os.path.exists(image_path):
            print(f"✗ Image not found: {image_path}")
            return False
        
        # Find and click the attach image button
        try:
            attach_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "[aria-label*='Attach'], [aria-label*='image'], button[class*='attach']"
                ))
            )
            attach_btn.click()
            time.sleep(2)  # Wait for file dialog to open
            print("✓ Clicked attach button, file dialog should be open")
            
            # Use pyautogui to interact with the native file dialog
            # On macOS, we can type the path directly
            time.sleep(1)
            
            # Press Cmd+Shift+G to open "Go to folder" dialog on macOS
            pyautogui.hotkey('command', 'shift', 'g')
            time.sleep(0.5)
            
            # Type the directory path
            dir_path = os.path.dirname(image_path)
            pyautogui.typewrite(dir_path, interval=0.02)
            time.sleep(0.3)
            pyautogui.press('enter')
            time.sleep(1)
            
            # Now type the filename
            filename = os.path.basename(image_path)
            pyautogui.typewrite(filename, interval=0.02)
            time.sleep(0.3)
            
            # Press Enter to select the file
            pyautogui.press('enter')
            time.sleep(2)
            
            print(f"✓ Attached photo: {filename}")
            return True
            
        except TimeoutException:
            print("✗ Could not find attach button")
            return False
        except Exception as e:
            print(f"✗ Error attaching photo: {e}")
            # Try to close any dialog with Escape
            pyautogui.press('escape')
            return False
    
    def send_message(self):
        """Click the send button"""
        try:
            send_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "button.msg-form__send-button, [aria-label*='Send'], button[type='submit']"
                ))
            )
            send_btn.click()
            time.sleep(2)
            print("✓ Message sent!")
            return True
        except TimeoutException:
            print("✗ Could not find send button")
            return False
    
    def send_message_with_photos(self, profile_url: str, message: str, image_paths: list):
        """
        Complete workflow: Open profile, compose message with photos, send.
        """
        print(f"\n{'='*60}")
        print("LINKEDIN MESSAGE WITH PHOTOS")
        print('='*60)
        print(f"Profile: {profile_url}")
        print(f"Message length: {len(message)} chars")
        print(f"Photos: {len(image_paths)}")
        print('='*60 + "\n")
        
        try:
            # Start browser and login
            self.start_browser()
            if not self.login_with_cookies():
                return False
            
            # Open profile message dialog
            if not self.open_profile_message(profile_url):
                return False
            
            # Type the message
            if not self.type_message(message):
                return False
            
            # Attach photos one by one
            for i, img_path in enumerate(image_paths):
                print(f"\nAttaching photo {i+1}/{len(image_paths)}: {img_path}")
                if not self.attach_photo_with_pyautogui(img_path):
                    print(f"Warning: Failed to attach {img_path}")
                time.sleep(1)
            
            # Send the message
            if not self.send_message():
                return False
            
            print("\n" + "="*60)
            print("✅ MESSAGE WITH PHOTOS SENT SUCCESSFULLY!")
            print("="*60)
            return True
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
            return False
        
        finally:
            # Keep browser open for verification
            input("\nPress Enter to close browser...")
            if self.driver:
                self.driver.quit()
    
    def close(self):
        if self.driver:
            self.driver.quit()


def main():
    """Main function to send LinkedIn message with photos"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Send LinkedIn message with photos")
    parser.add_argument("profile_dir", help="Path to the profile directory (e.g., output/ashutosh-lath)")
    parser.add_argument("--profile-url", help="LinkedIn profile URL (optional, reads from profile_data.json if not provided)")
    args = parser.parse_args()
    
    profile_dir = args.profile_dir
    
    # Load profile data
    profile_data_path = os.path.join(profile_dir, 'profile_data.json')
    if os.path.exists(profile_data_path):
        with open(profile_data_path, 'r') as f:
            profile_data = json.load(f)
        profile_url = args.profile_url or profile_data.get('basic_info', {}).get('profile_url')
        first_name = profile_data.get('basic_info', {}).get('first_name', 'there')
    else:
        profile_url = args.profile_url
        first_name = "there"
    
    if not profile_url:
        print("Error: Could not determine profile URL")
        return
    
    # Load editorial teardown data
    teardown_dir = os.path.join(profile_dir, 'editorial_teardown')
    diagnoses_path = os.path.join(profile_dir, 'diagnoses.json')
    
    # Get teardown images
    image_paths = []
    if os.path.exists(teardown_dir):
        for f in sorted(os.listdir(teardown_dir)):
            if f.endswith('.png'):
                image_paths.append(os.path.join(teardown_dir, f))
    
    # Get verdict from diagnoses
    verdict = "Needs work"
    gap = "Your profile lacks clarity."
    if os.path.exists(diagnoses_path):
        with open(diagnoses_path, 'r') as f:
            diagnoses = json.load(f)
        profile_diag = diagnoses.get('profile', {})
        verdict = profile_diag.get('one_sentence_verdict', verdict)
        gap = profile_diag.get('consequence', gap)
    
    # Compose message
    message = f"""Hey {first_name}! 👋

I ran your profile through my editorial teardown engine. Honest verdict:

"{verdict}"

{gap}

I put together a visual breakdown with specific fixes (attached). I marked exactly where you're losing people.

I run a personal branding agency and we help founders like you turn "building cool stuff" into content that actually converts.

Want the full playbook?"""
    
    print("\n" + "="*60)
    print("MESSAGE PREVIEW")
    print("="*60)
    print(message)
    print("="*60)
    print(f"\nImages to attach: {len(image_paths)}")
    for img in image_paths:
        print(f"  - {os.path.basename(img)}")
    
    confirm = input("\nType 'SEND' to confirm: ")
    if confirm.upper() != 'SEND':
        print("Cancelled.")
        return
    
    # Send message
    messenger = LinkedInPhotoMessenger()
    messenger.send_message_with_photos(profile_url, message, image_paths)


if __name__ == "__main__":
    main()





