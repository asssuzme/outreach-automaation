#!/usr/bin/env python3
"""
Send a simple LinkedIn message without images.
This is a standalone script that can be run directly.
"""

import os
import sys
import time
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException


def get_driver():
    """Create Chrome driver with proper options."""
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    
    chromium_path = shutil.which('chromium') or shutil.which('google-chrome')
    if chromium_path:
        options.binary_location = chromium_path
    
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
    })
    return driver


def send_linkedin_message(profile_url: str, message: str) -> bool:
    """Send a LinkedIn message to a profile."""
    
    li_at = os.environ.get('LINKEDIN_LI_AT')
    jsessionid = os.environ.get('LINKEDIN_JSESSIONID', '')
    
    if not li_at:
        print("ERROR: LINKEDIN_LI_AT not set")
        return False
    
    print(f"\n{'='*60}")
    print("SENDING LINKEDIN MESSAGE")
    print(f"{'='*60}")
    print(f"Profile: {profile_url}")
    print(f"Message length: {len(message)} chars")
    print(f"{'='*60}\n")
    
    driver = None
    try:
        print("[1/5] Starting browser...")
        driver = get_driver()
        print("✓ Browser started")
        
        print("[2/5] Logging in with cookies...")
        driver.get("https://www.linkedin.com")
        time.sleep(2)
        
        driver.add_cookie({
            'name': 'li_at',
            'value': li_at,
            'domain': '.linkedin.com',
            'path': '/',
            'secure': True
        })
        print("   ✓ Added li_at cookie")
        
        if jsessionid:
            driver.add_cookie({
                'name': 'JSESSIONID',
                'value': jsessionid,
                'domain': '.linkedin.com',
                'path': '/',
                'secure': True
            })
            print("   ✓ Added JSESSIONID cookie")
        
        driver.get("https://www.linkedin.com/feed/")
        time.sleep(3)
        
        if 'login' in driver.current_url or 'authwall' in driver.current_url:
            print("✗ Login failed - cookies may be expired")
            return False
        print("✓ Logged in successfully")
        
        print(f"[3/5] Opening profile: {profile_url}")
        driver.get(profile_url)
        time.sleep(4)
        
        print("[4/5] Finding and clicking Message button...")
        msg_btn = None
        
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            aria = btn.get_attribute("aria-label") or ""
            text = btn.text or ""
            if "Message" in aria or text.strip() == "Message":
                msg_btn = btn
                break
        
        if not msg_btn:
            try:
                msg_btn = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Message')]")
            except:
                pass
        
        if msg_btn:
            try:
                msg_btn.click()
            except:
                driver.execute_script("arguments[0].click();", msg_btn)
            time.sleep(3)
            print("✓ Message dialog opened")
        else:
            print("   No direct Message button, trying More → Message...")
            more_btn = None
            for btn in buttons:
                aria = btn.get_attribute("aria-label") or ""
                if "More" in aria:
                    more_btn = btn
                    break
            
            if not more_btn:
                try:
                    more_btn = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'More')]")
                except:
                    pass
            
            if more_btn:
                driver.execute_script("arguments[0].click();", more_btn)
                time.sleep(2)
                print("   ✓ Clicked More button")
                
                try:
                    msg_option = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[text()='Message']/ancestor::*[@role='button' or @role='menuitem' or self::li or self::div[contains(@class,'dropdown')]]"))
                    )
                    msg_option.click()
                    time.sleep(3)
                    print("✓ Message/InMail dialog opened via More menu")
                except:
                    driver.save_screenshot("debug_more_menu.png")
                    print("✗ Could not find Message option in More menu")
                    print("   Screenshot saved to debug_more_menu.png")
                    return False
            else:
                driver.save_screenshot("debug_no_buttons.png")
                print("✗ Could not find Message or More button")
                print("   Screenshot saved to debug_no_buttons.png")
                return False
        
        print("[5/5] Typing and sending message...")
        msg_input = None
        
        for selector in [".msg-form__contenteditable", "div[role='textbox'][contenteditable='true']"]:
            try:
                msg_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if msg_input:
                    break
            except:
                continue
        
        if not msg_input:
            print("✗ Could not find message input box")
            return False
        
        msg_input.click()
        time.sleep(0.5)
        ActionChains(driver).send_keys(message).perform()
        time.sleep(1)
        print("✓ Message typed")
        
        send_btn = None
        for selector in ["button.msg-form__send-button", "button[type='submit']"]:
            try:
                send_btn = driver.find_element(By.CSS_SELECTOR, selector)
                if send_btn and send_btn.is_enabled():
                    break
            except:
                continue
        
        if send_btn:
            send_btn.click()
            time.sleep(2)
            print("✓ MESSAGE SENT SUCCESSFULLY!")
            return True
        else:
            print("✗ Could not find Send button")
            return False
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python send_simple_message.py <profile_url> [message]")
        sys.exit(1)
    
    profile_url = sys.argv[1]
    message = sys.argv[2] if len(sys.argv) > 2 else "Hey! I came across your profile and thought we should connect. Would love to chat!"
    
    success = send_linkedin_message(profile_url, message)
    sys.exit(0 if success else 1)
