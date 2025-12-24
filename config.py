"""Configuration file for LinkedIn Profile Scraper."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Apify API Configuration
APIFY_API_KEY = os.getenv("APIFY_API_KEY", "apify_api_hUYzNzjiNgxaG8vZV8BBBUIEbFRgAD4q068q")
APIFY_API_BASE_URL = "https://api.apify.com/v2"
LINKEDIN_PROFILE_ACTOR = "apimaestro/linkedin-profile-detail"
LINKEDIN_POSTS_ACTOR = "apimaestro/linkedin-profile-posts"

# Output directory for saved files
OUTPUT_DIR = "output"

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")  # Vision-capable model for screenshot analysis

# KIE.ai (Nano Banana Pro) Configuration
KIE_AI_API_KEY = os.getenv("KIE_AI_API_KEY", "6e2171d53ecc1a5072fedbbf89ab530b")
KIE_AI_BASE_URL = os.getenv("KIE_AI_BASE_URL", "https://api.kie.ai")
KIE_AI_MODEL = os.getenv("KIE_AI_MODEL", "nano-banana-pro")

# Anthropic API Configuration (for Claude 3.5 Sonnet Vision)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Google Gemini API Configuration (for Nano Banana image-to-image)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBqorFwB99V4EQ5QZsVrx3TkCIqMYYzUfY")
GEMINI_TEXT_MODEL = "gemini-2.5-flash"  # For analysis (FREE)
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"  # Fast, 1024px (Nano Banana)
GEMINI_IMAGE_MODEL_PRO = "gemini-3-pro-image-preview"  # Pro, up to 4K (Nano Banana Pro)

# Agency Configuration
AGENCY_NAME = os.getenv("AGENCY_NAME", "Your Marketing Agency")
AGENCY_EMAIL = os.getenv("AGENCY_EMAIL", "contact@youragency.com")
AGENCY_WEBSITE = os.getenv("AGENCY_WEBSITE", "https://youragency.com")
