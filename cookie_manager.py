"""Cookie management for LinkedIn authentication."""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from config import OUTPUT_DIR


class CookieManager:
    """Manages LinkedIn authentication cookies."""
    
    DEFAULT_COOKIE_FILE = "linkedin_cookies.json"
    
    def __init__(self, cookie_file: str = None):
        """
        Initialize cookie manager.
        
        Args:
            cookie_file: Path to cookie file. If None, uses default.
        """
        self.cookie_file = cookie_file or self.DEFAULT_COOKIE_FILE
        self.cookie_path = Path(self.cookie_file)
    
    def load_cookies(self) -> Optional[Dict[str, str]]:
        """
        Load cookies from file.
        
        Returns:
            Dictionary of cookies or None if file doesn't exist
        """
        if not self.cookie_path.exists():
            return None
        
        try:
            with open(self.cookie_path, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
                # Validate that we have at least li_at
                if 'li_at' in cookies:
                    return cookies
                else:
                    print("Warning: Cookie file exists but missing 'li_at' cookie.")
                    return None
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in cookie file: {e}")
            return None
        except Exception as e:
            print(f"Error loading cookies: {e}")
            return None
    
    def save_cookies(self, cookies: Dict[str, str]) -> bool:
        """
        Save cookies to file.
        
        Args:
            cookies: Dictionary of cookie names and values
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure we have li_at at minimum
            if 'li_at' not in cookies:
                raise ValueError("Cookies must include 'li_at' (main authentication cookie)")
            
            with open(self.cookie_path, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2)
            
            # Set restricted file permissions (owner read/write only)
            os.chmod(self.cookie_path, 0o600)
            
            print(f"✓ Cookies saved to {self.cookie_path}")
            return True
        except Exception as e:
            print(f"Error saving cookies: {e}")
            return False
    
    def cookies_to_playwright_format(self, cookies: Dict[str, str]) -> List[Dict]:
        """
        Convert cookie dictionary to Playwright cookie format.
        
        Args:
            cookies: Dictionary of cookie names and values
            
        Returns:
            List of cookies in Playwright format
        """
        playwright_cookies = []
        
        for name, value in cookies.items():
            # Use .linkedin.com domain (works for all LinkedIn subdomains)
            cookie = {
                'name': name,
                'value': value,
                'domain': '.linkedin.com',
                'path': '/',
            }
            playwright_cookies.append(cookie)
        
        return playwright_cookies
    
    def validate_cookies(self, cookies: Dict[str, str]) -> bool:
        """
        Validate that cookies contain required fields.
        
        Args:
            cookies: Dictionary of cookies to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not cookies:
            return False
        
        if 'li_at' not in cookies:
            return False
        
        # li_at should not be empty
        if not cookies['li_at'] or not cookies['li_at'].strip():
            return False
        
        return True
    
    def get_cookie_file_path(self) -> str:
        """Get the path to the cookie file."""
        return str(self.cookie_path.absolute())

