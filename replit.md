# LinkedIn Profile Scraper & Outreach Automation

## Overview
A Python-based LinkedIn profile scraping and outreach automation tool. It uses Apify APIs to scrape profile data and posts, captures screenshots, annotates them using AI (Google Gemini), and generates personalized outreach emails.

## Project Structure
```
.
├── cloud-run-handler.py    # Flask HTTP handler (main web server)
├── main.py                 # CLI entry point for single profile processing
├── batch_processor.py      # Batch processing for multiple profiles
├── apify_client.py         # Apify API wrapper for LinkedIn scraping
├── config.py               # Configuration and environment variables
├── requirements.txt        # Python dependencies
├── output/                 # Generated output files (profiles, screenshots)
└── linkedin_cookies.json   # LinkedIn session cookies (not in repo)
```

## Key Components
- **Flask API Server** (`cloud-run-handler.py`): HTTP endpoints for batch processing
- **Profile Scraper** (`apify_client.py`): Uses Apify to fetch LinkedIn data
- **Screenshot Capture**: Uses undetected-chromedriver for authenticated screenshots
- **AI Annotation** (`nano_banana_annotator.py`): Annotates screenshots via Google Gemini
- **Email Generator** (`generate_email_nano.py`): Creates personalized outreach emails

## API Endpoints
- `GET /` - Health check
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

## Notes
- LinkedIn cookies (`linkedin_cookies.json`) must be provided separately for screenshot functionality
- This is an API backend service - the main endpoint returns JSON
