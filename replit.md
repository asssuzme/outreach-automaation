# LinkedIn Profile Scraper & Outreach Automation

## Overview
A Python-based LinkedIn profile scraping and outreach automation tool with a web frontend. It uses Apify APIs to scrape profile data and posts, captures screenshots, annotates them using AI (Google Gemini), and generates personalized outreach emails.

## Project Structure
```
.
├── cloud-run-handler.py    # Flask HTTP handler (main web server)
├── templates/index.html    # Frontend UI
├── main.py                 # CLI entry point for single profile processing
├── batch_processor.py      # Batch processing for multiple profiles
├── apify_client.py         # Apify API wrapper for LinkedIn scraping
├── config.py               # Configuration and environment variables
├── requirements.txt        # Python dependencies
├── output/                 # Generated output files (profiles, screenshots)
└── linkedin_cookies.json   # LinkedIn session cookies (saved via frontend)
```

## Key Components
- **Web Frontend** (`templates/index.html`): User interface for profile URLs and cookie management
- **Flask API Server** (`cloud-run-handler.py`): HTTP endpoints for batch processing
- **Profile Scraper** (`apify_client.py`): Uses Apify to fetch LinkedIn data
- **Screenshot Capture**: Uses undetected-chromedriver for authenticated screenshots
- **AI Annotation** (`nano_banana_annotator.py`): Annotates screenshots via Google Gemini
- **Email Generator** (`generate_email_nano.py`): Creates personalized outreach emails

## API Endpoints
- `GET /` - Frontend UI
- `GET /api/status` - API status check
- `GET /api/cookies/status` - Check if LinkedIn cookies are configured
- `POST /api/cookies` - Save LinkedIn cookies
- `POST /run` - Trigger batch processing with profile URLs
- `POST /run-file` - Process profiles from a file

## Environment Variables Required
- `APIFY_API_KEY` - Apify API key for LinkedIn scraping
- `OPENAI_API_KEY` - OpenAI API key (optional)
- `GEMINI_API_KEY` - Google Gemini API key for image annotation
- `ANTHROPIC_API_KEY` - Anthropic API key (optional)

## Running Locally
The Flask server runs on port 5000:
```bash
python cloud-run-handler.py
```

## Usage
1. Open the web interface
2. Configure LinkedIn cookies (expand "Configure LinkedIn Cookies" section)
3. Enter LinkedIn profile URLs (one per line)
4. Click "Process Profiles" to start automation

## Notes
- LinkedIn cookies can be configured via the web frontend
- Screenshots require valid LinkedIn session cookies
