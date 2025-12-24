#!/usr/bin/env python3
"""
Send LinkedIn message with photos - Non-interactive version

Usage:
    python send_with_photos.py <profile_url> <message_file> <image1> [image2] ...

Or to use from the workflow:
    python send_with_photos.py --profile-dir <path>
"""

import os
import sys
import time
import json
import subprocess
from pathlib import Path

# Auto-install packages
def ensure_packages():
    pkgs = ['selenium', 'undetected-chromedriver']
    for p in pkgs:
        try:
            __import__(p.replace('-', '_'))
        except ImportError:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', p, '-q'])

ensure_packages()

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc


def load_cookies(file_path="linkedin_cookies.json"):
    """Load LinkedIn cookies from environment secrets or file."""
    li_at = os.environ.get('LINKEDIN_LI_AT')
    if li_at:
        return {
            'li_at': li_at,
            'JSESSIONID': os.environ.get('LINKEDIN_JSESSIONID', '')
        }
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    raise FileNotFoundError("LinkedIn cookies not configured")


def send_message_with_photos(profile_url: str, message: str, image_paths: list, cookies_file: str = "linkedin_cookies.json"):
    """
    Send a LinkedIn message with photos attached.
    Uses Selenium's file input method for uploading.
    """
    
    print("\n" + "="*60)
    print("LINKEDIN MESSAGE WITH PHOTOS")
    print("="*60)
    print(f"Profile: {profile_url}")
    print(f"Message: {len(message)} chars")
    print(f"Images: {len(image_paths)}")
    print("="*60)
    
    # Verify images exist
    for img in image_paths:
        if not os.path.exists(img):
            print(f"ERROR: Image not found: {img}")
            return False
    
    # Start browser
    print("\n[1/6] Starting browser...")
    options = uc.ChromeOptions()
    options.add_argument('--start-maximized')
    options.add_argument('--disable-blink-features=AutomationControlled')
    driver = uc.Chrome(options=options)
    
    try:
        # Load cookies and login
        print("[2/6] Logging in with cookies...")
        cookies = load_cookies(cookies_file)
        
        # First navigate to LinkedIn to establish domain
        driver.get("https://www.linkedin.com/uas/login")
        time.sleep(2)
        
        # Clear any existing cookies and add our session cookies
        driver.delete_all_cookies()
        
        for name, value in cookies.items():
            if name in ['li_at', 'JSESSIONID']:
                try:
                    driver.add_cookie({
                        'name': name, 
                        'value': value,
                        'domain': '.linkedin.com', 
                        'path': '/',
                        'secure': True
                    })
                    print(f"   ✓ Added cookie: {name}")
                except Exception as e:
                    print(f"   ⚠ Cookie error: {e}")
        
        # Navigate to feed to verify login
        driver.get("https://www.linkedin.com/feed/")
        time.sleep(4)
        
        # Verify login
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='feed'], [class*='global-nav']"))
            )
            print("✓ Logged in successfully")
        except TimeoutException:
            print("✗ Login failed - cookies may be expired")
            return False
        
        # Navigate to profile
        print(f"[3/6] Opening profile...")
        driver.get(profile_url)
        time.sleep(5)  # Wait longer for page to load
        
        # Wait for profile content to load
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='profile'], [class*='pvs-profile']"))
            )
        except:
            pass  # Continue anyway
        
        # Click Message button (or More -> Message for InMail)
        print("[4/6] Opening message dialog...")
        try:
            # First try direct Message button (could be "Message" or "Message [Name]")
            try:
                # Try multiple approaches
                msg_btn = None
                # Approach 1: XPath with aria-label
                try:
                    msg_btn = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//button[contains(@aria-label, 'Message')]"))
                    )
                except:
                    pass
                
                # Approach 2: Find all buttons and filter
                if not msg_btn:
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    for btn in buttons:
                        aria_label = btn.get_attribute("aria-label") or ""
                        if "Message" in aria_label:
                            msg_btn = btn
                            break
                
                if msg_btn:
                    # Try normal click first
                    try:
                        msg_btn.click()
                    except:
                        # If normal click fails, use JavaScript
                        driver.execute_script("arguments[0].click();", msg_btn)
                    time.sleep(3)
                    print("✓ Message dialog opened (direct)")
                else:
                    raise Exception("Message button not found")
            except TimeoutException:
                # If not connected, try More -> Message (InMail)
                print("   Direct Message not available, trying More -> Message (InMail)...")
                # Try multiple selectors for More button
                more_selectors = [
                    "//button[@aria-label='More actions']",
                    "//button[contains(@aria-label, 'More actions')]",
                    "//button[contains(@aria-label, 'More')]",
                    "//button[.//span[text()='More']]",
                    "//div[contains(@class, 'pvs-profile-actions')]//button[contains(@aria-label, 'More')]"
                ]
                more_btn = None
                for selector in more_selectors:
                    try:
                        more_btn = WebDriverWait(driver, 2).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        if more_btn:
                            break
                    except:
                        continue
                
                if more_btn:
                    more_btn.click()
                    time.sleep(1.5)
                    print("   ✓ Clicked More button")
                    
                    # Click Message from dropdown - try multiple selectors
                    msg_selectors = [
                        "//span[text()='Message']/ancestor::div[@role='button']",
                        "//div[contains(@class, 'artdeco-dropdown__item')][.//span[text()='Message']]",
                        "//li[.//span[text()='Message']]",
                        "//div[@role='menuitem'][.//span[text()='Message']]"
                    ]
                    msg_option = None
                    for selector in msg_selectors:
                        try:
                            msg_option = WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                            if msg_option:
                                break
                        except:
                            continue
                    
                    if msg_option:
                        msg_option.click()
                        time.sleep(2)
                        print("✓ InMail dialog opened")
                    else:
                        raise Exception("Could not find Message option in dropdown")
                else:
                    # Debug: List all buttons on page
                    print("   DEBUG: Listing all buttons on page...")
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    for i, btn in enumerate(buttons[:15]):
                        txt = btn.text[:40] if btn.text else btn.get_attribute("aria-label")[:40] if btn.get_attribute("aria-label") else "no text"
                        print(f"   Button {i}: {txt}")
                    raise Exception("Could not find More button")
        except TimeoutException:
            print("✗ Could not find Message button or More menu")
            return False
        
        # Type message
        print("[5/6] Typing message and attaching images...")
        try:
            # Find message input (could be contenteditable or textarea)
            msg_input = None
            selectors = [
                ".msg-form__contenteditable",
                "div[role='textbox'][contenteditable='true']",
                "[data-artdeco-is-focused]",
                ".msg-form__msg-content-container [contenteditable='true']"
            ]
            
            for selector in selectors:
                try:
                    msg_input = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if msg_input:
                        break
                except:
                    continue
            
            if not msg_input:
                print("✗ Could not find message input")
                return False
            
            # Click and type
            msg_input.click()
            time.sleep(0.5)
            
            # Type message
            ActionChains(driver).send_keys(message).perform()
            time.sleep(1)
            print("✓ Message typed")
            
        except Exception as e:
            print(f"✗ Error typing message: {e}")
            return False
        
        # Attach images
        if image_paths:
            print("   Attaching images...")
            
            # Find file input elements
            file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            
            if file_inputs:
                for img_path in image_paths:
                    abs_path = os.path.abspath(img_path)
                    try:
                        # Make file input interactable
                        driver.execute_script("""
                            arguments[0].style.display = 'block';
                            arguments[0].style.visibility = 'visible';
                            arguments[0].style.opacity = '1';
                            arguments[0].style.height = 'auto';
                            arguments[0].style.width = 'auto';
                        """, file_inputs[0])
                        
                        file_inputs[0].send_keys(abs_path)
                        time.sleep(2)  # Wait for upload
                        print(f"   ✓ Attached: {os.path.basename(img_path)}")
                    except Exception as e:
                        print(f"   ⚠ Could not attach {os.path.basename(img_path)}: {e}")
            else:
                # Try clicking the attach button to reveal file input
                try:
                    attach_btn = driver.find_element(By.CSS_SELECTOR, "[aria-label*='Attach'], button[class*='attach']")
                    attach_btn.click()
                    time.sleep(1)
                    
                    # Look for file input again
                    file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                    if file_inputs:
                        for img_path in image_paths:
                            file_inputs[0].send_keys(os.path.abspath(img_path))
                            time.sleep(2)
                            print(f"   ✓ Attached: {os.path.basename(img_path)}")
                except Exception as e:
                    print(f"   ⚠ Could not find attach button: {e}")
        
        # Send message
        print("[6/6] Sending message...")
        try:
            send_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 
                    "button.msg-form__send-button, "
                    "button[type='submit'][class*='send'], "
                    "button[aria-label*='Send']"
                ))
            )
            
            # Make sure button is enabled
            time.sleep(2)
            if not send_btn.is_enabled():
                print("⚠ Send button is disabled - checking why...")
                # Check if there's an error message
                try:
                    error_msg = driver.find_element(By.CSS_SELECTOR, "[class*='error'], [class*='warning']")
                    print(f"   Error: {error_msg.text[:100]}")
                except:
                    pass
                print("   Please check the message in the browser and send manually if needed.")
                input("   Press ENTER after reviewing...")
                return False
            
            # Click send button (first click - opens popup)
            send_btn.click()
            print("   ✓ Clicked Send button (first click)")
            time.sleep(5)  # Wait longer for popup to fully appear
            
            # Wait for popup and click Send again
            print("   Waiting for confirmation popup...")
            time.sleep(2)
            
            # Strategy 1: Wait for dialog/modal to appear, then find Send button inside
            try:
                # Wait for a dialog/modal to appear
                dialog = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, 
                        "//div[@role='dialog'] | //div[contains(@class, 'artdeco-modal')] | //div[contains(@class, 'msg-overlay')]"
                    ))
                )
                print("   ✓ Found dialog/modal popup")
                
                # Find Send button inside the dialog
                popup_send = dialog.find_element(By.XPATH, 
                    ".//button[contains(@aria-label, 'Send') or contains(text(), 'Send')]"
                )
                
                if popup_send and popup_send.is_displayed():
                    print("   ✓ Found Send button in popup - clicking...")
                    driver.execute_script("arguments[0].click();", popup_send)
                    print("   ✓ Clicked Send on popup")
                    time.sleep(3)
                else:
                    raise Exception("Send button not found in dialog")
                    
            except TimeoutException:
                # Strategy 2: No dialog found, try finding any Send button that's different from original
                print("   No dialog found - looking for any Send button...")
                try:
                    all_send_btns = driver.find_elements(By.XPATH, 
                        "//button[contains(@aria-label, 'Send')]"
                    )
                    
                    for btn in all_send_btns:
                        if btn.is_displayed() and btn != send_btn:
                            print("   ✓ Found different Send button - clicking...")
                            driver.execute_script("arguments[0].click();", btn)
                            print("   ✓ Clicked Send")
                            time.sleep(3)
                            break
                    else:
                        print("   ⚠ No popup Send button found - message may have been sent")
                except Exception as e:
                    print(f"   ⚠ Could not find popup Send button: {str(e)[:60]}")
            except Exception as e:
                print(f"   ⚠ Error handling popup: {str(e)[:60]}")
            
            print("\n" + "="*60)
            print("✅ MESSAGE SENT!")
            print("="*60)
            
        except TimeoutException:
            print("✗ Could not find send button")
            print("   Browser will stay open - please send manually")
            input("   Press ENTER after sending...")
            return False
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False
    
    finally:
        print("\n" + "="*60)
        print("⚠️ Keeping browser open for 10 seconds for verification...")
        print("="*60)
        time.sleep(10)
        print("\nClosing browser...")
        driver.quit()
        print("✓ Browser closed.")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Send LinkedIn message with photos")
    parser.add_argument("--profile-dir", help="Profile directory (auto-extracts data)")
    parser.add_argument("--profile-url", help="LinkedIn profile URL")
    parser.add_argument("--message", help="Message text (or path to .txt file)")
    parser.add_argument("--images", nargs="*", help="Image file paths")
    parser.add_argument("--cookies", default="linkedin_cookies.json", help="Cookies file")
    
    args = parser.parse_args()
    
    # Extract data from profile directory if provided
    if args.profile_dir:
        profile_dir = args.profile_dir
        
        # Load profile data
        with open(os.path.join(profile_dir, 'profile_data.json')) as f:
            profile = json.load(f)
        
        profile_url = args.profile_url or profile.get('basic_info', {}).get('profile_url')
        first_name = profile.get('basic_info', {}).get('first_name', 'there')
        
        # Generate professional agency-focused message
        message = f"""Hey {first_name}! 👋

I run a personal branding agency, and I personally took some time to do a complete breakdown of your LinkedIn profile. 

I've attached an annotated snapshot that shows exactly where your profile is losing people and what specific fixes would make the biggest impact.

I'd love to discuss this further with you - happy to hop on a quick call to walk you through the full breakdown and answer any questions. Would that be helpful?"""
        
        # Get images (prefer Nano Banana output)
        images = []
        nano_dir = os.path.join(profile_dir, 'nano_banana_annotated')
        if os.path.exists(nano_dir):
            profile_img = os.path.join(nano_dir, 'profile.png')
            if os.path.exists(profile_img):
                images.append(profile_img)
            # Attach first post annotation if present
            post1 = os.path.join(nano_dir, 'post_1.png')
            if os.path.exists(post1):
                images.append(post1)
        images = args.images or images
        
    else:
        profile_url = args.profile_url
        if args.message and os.path.exists(args.message):
            with open(args.message) as f:
                message = f.read()
        else:
            message = args.message or "Hello!"
        images = args.images or []
    
    if not profile_url:
        print("Error: Profile URL required")
        return
    
    # Run
    success = send_message_with_photos(profile_url, message, images, args.cookies)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

