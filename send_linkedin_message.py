"""
Send LinkedIn Message - Uses Selenium to send a personalized message on LinkedIn.
"""

import os
import sys
import json
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from cookie_manager import CookieManager


def load_profile_data(profile_dir: str) -> dict:
    """Load profile data from directory."""
    profile_path = os.path.join(profile_dir, 'profile_data.json')
    with open(profile_path, 'r') as f:
        return json.load(f)


def load_editorial_summary(profile_dir: str) -> dict:
    """Load editorial V3 summary."""
    summary_path = os.path.join(profile_dir, 'editorial_v3', 'summary.json')
    if os.path.exists(summary_path):
        with open(summary_path, 'r') as f:
            return json.load(f)
    return {}


def generate_linkedin_message(profile_data: dict, summary: dict) -> str:
    """
    Generate a short, punchy LinkedIn message.
    
    LinkedIn DMs should be short - under 300 characters ideally.
    """
    first_name = profile_data.get('basic_info', {}).get('first_name', 'there')
    verdict = summary.get('profile', {}).get('verdict', 'needs work')
    gap = summary.get('profile', {}).get('the_gap', '')
    
    message = f"""Hey {first_name}! 👋

I came across your profile and spent some time looking through it. Honest take: "{verdict}"

{gap}

I run a personal branding agency and we help people like you transform their LinkedIn presence. Would love to share a detailed breakdown I put together for you.

Interested?"""
    
    return message


def send_message(profile_url: str, message: str, cookies_file: str = "linkedin_cookies.json"):
    """
    Send a LinkedIn message using Selenium.
    
    Args:
        profile_url: LinkedIn profile URL
        message: Message to send
        cookies_file: Path to cookies file
    """
    print(f"\n{'='*60}")
    print("LINKEDIN MESSAGE SENDER")
    print(f"{'='*60}")
    print(f"Profile: {profile_url}")
    print(f"Message length: {len(message)} characters")
    print(f"{'='*60}\n")
    
    # Initialize browser
    print("[1/5] Starting browser...")
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    driver = uc.Chrome(options=options)
    
    try:
        # Load cookies
        print("[2/5] Loading LinkedIn session...")
        cookie_manager = CookieManager(cookies_file)
        cookies = cookie_manager.load_cookies()
        
        # Navigate to LinkedIn first to set cookies
        driver.get("https://www.linkedin.com")
        time.sleep(2)
        
        # Apply cookies
        for cookie in cookies:
            try:
                cookie_dict = {
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': '.linkedin.com'
                }
                driver.add_cookie(cookie_dict)
            except Exception as e:
                pass
        
        # Refresh to apply cookies
        driver.refresh()
        time.sleep(3)
        
        # Navigate to profile
        print(f"[3/5] Navigating to profile...")
        driver.get(profile_url)
        time.sleep(4)
        
        # Click Message button
        print("[4/5] Opening message dialog...")
        try:
            # Try different selectors for the Message button
            message_btn = None
            selectors = [
                "//button[contains(@aria-label, 'Message')]",
                "//button[contains(text(), 'Message')]",
                "//span[text()='Message']/ancestor::button",
                ".message-anywhere-button",
                "[data-control-name='message']"
            ]
            
            for selector in selectors:
                try:
                    if selector.startswith("//"):
                        message_btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    elif selector.startswith("."):
                        message_btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    else:
                        message_btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    if message_btn:
                        break
                except:
                    continue
            
            if not message_btn:
                raise Exception("Could not find Message button")
            
            message_btn.click()
            time.sleep(3)
            
        except Exception as e:
            print(f"  ⚠️ Could not click Message button: {e}")
            print("  Trying direct messaging URL...")
            
            # Extract profile ID and go to messaging directly
            profile_id = profile_url.rstrip('/').split('/')[-1]
            driver.get(f"https://www.linkedin.com/messaging/compose/?recipient={profile_id}")
            time.sleep(4)
        
        # Type the message
        print("[5/5] Sending message...")
        try:
            # Find the message input field
            msg_input = None
            input_selectors = [
                "div.msg-form__contenteditable",
                "[role='textbox']",
                ".msg-form__msg-content-container div[contenteditable='true']",
                "div[data-placeholder='Write a message…']"
            ]
            
            for selector in input_selectors:
                try:
                    msg_input = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if msg_input:
                        break
                except:
                    continue
            
            if not msg_input:
                raise Exception("Could not find message input field")
            
            # Click to focus
            msg_input.click()
            time.sleep(1)
            
            # Type message
            msg_input.send_keys(message)
            time.sleep(2)
            
            # Find and click Send button
            send_btn = None
            send_selectors = [
                "//button[contains(@class, 'msg-form__send-button')]",
                "//button[text()='Send']",
                ".msg-form__send-button",
                "button[type='submit']"
            ]
            
            for selector in send_selectors:
                try:
                    if selector.startswith("//"):
                        send_btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        send_btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    if send_btn:
                        break
                except:
                    continue
            
            if send_btn:
                send_btn.click()
                print("\n✅ MESSAGE SENT!")
                time.sleep(3)
            else:
                print("\n⚠️ Could not find Send button. Message typed but not sent.")
                print("   Please manually click Send in the browser.")
                input("   Press Enter after sending...")
                
        except Exception as e:
            print(f"\n⚠️ Error typing message: {e}")
            print("   Browser is open - you can manually send the message.")
            input("   Press Enter when done...")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    finally:
        print("\nClosing browser in 5 seconds...")
        time.sleep(5)
        driver.quit()


def main(profile_dir: str, dry_run: bool = False):
    """
    Main function to generate and send LinkedIn message.
    
    Args:
        profile_dir: Path to profile output directory
        dry_run: If True, only show message without sending
    """
    # Load data
    print("Loading profile data...")
    profile_data = load_profile_data(profile_dir)
    summary = load_editorial_summary(profile_dir)
    
    # Get profile URL
    profile_url = profile_data.get('basic_info', {}).get('profile_url', '')
    if not profile_url:
        raise ValueError("No profile URL found in profile data")
    
    # Generate message
    message = generate_linkedin_message(profile_data, summary)
    
    print("\n" + "="*60)
    print("MESSAGE PREVIEW")
    print("="*60)
    print(message)
    print("="*60)
    print(f"\nCharacter count: {len(message)}")
    
    if dry_run:
        print("\n[DRY RUN] Message not sent.")
        return message
    
    # Confirm before sending
    print("\n⚠️  Ready to send this message on LinkedIn.")
    confirm = input("Type 'SEND' to confirm: ")
    
    if confirm.strip().upper() == 'SEND':
        send_message(profile_url, message)
    else:
        print("Cancelled.")
    
    return message


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python send_linkedin_message.py <profile_dir>")
        print("  python send_linkedin_message.py <profile_dir> --dry-run")
        print("\nExample:")
        print("  python send_linkedin_message.py output/jainjatin2525")
        sys.exit(1)
    
    profile_dir = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    
    main(profile_dir, dry_run)





