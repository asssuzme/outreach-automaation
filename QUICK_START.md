# Quick Start Guide - LinkedIn Outreach Automation

## What This System Does

**Complete end-to-end automation:** Takes a LinkedIn profile URL → Scrapes data → Captures screenshots → AI annotates them → **Sends personalized LinkedIn message with annotated images**

## Complete Workflow

```
LinkedIn Profile URL
    ↓
1. Scrape Profile Data (Apify API)
    ↓
2. Scrape Posts Data (Apify API)
    ↓
3. Capture Screenshots (Selenium + Chrome)
    ↓
4. AI Annotation (Google Gemini API)
    ↓
5. Generate Outreach Email (Optional)
    ↓
6. Send LinkedIn Message (Selenium Automation)
    ↓
✅ Message Sent to LinkedIn Profile
```

## Quick Commands

### Single Profile
```bash
# Process and send message
python3 main.py https://www.linkedin.com/in/username
python3 send_with_photos.py --profile-dir output/username
```

### Batch Processing
```bash
# Process multiple profiles and send messages automatically
python3 batch_processor.py --profiles-file profiles_batch.txt
```

## Key Files

- `main.py` - Scrapes and captures screenshots
- `nano_banana_annotator.py` - AI annotation engine
- `send_with_photos.py` - LinkedIn message sending
- `batch_processor.py` - Batch processing orchestrator

## Required Setup

1. **API Keys** (in `.env`):
   - `APIFY_API_KEY` - For LinkedIn scraping
   - `GEMINI_API_KEY` - For image annotation
   - `OPENAI_API_KEY` - Optional, for email generation

2. **LinkedIn Cookies** (`linkedin_cookies.json`):
   - Export from browser after logging into LinkedIn
   - Required for screenshot capture and message sending

## Output Structure

```
output/{profile_id}/
├── profile_data.json          # Scraped data
├── screenshot.png              # Profile screenshot
├── nano_banana_annotated/
│   └── profile.png            # AI-annotated image
└── outreach_email_nano.html   # Generated email
```

## Message Sent

The system automatically sends a LinkedIn message like:

> "Hey {name}! 👋
> 
> I run a personal branding agency, and I personally took some time to do a complete breakdown of your LinkedIn profile. 
> 
> I've attached an annotated snapshot that shows exactly where your profile is losing people and what specific fixes would make the biggest impact.
> 
> I'd love to discuss this further with you - happy to hop on a quick call to walk you through the full breakdown and answer any questions. Would that be helpful?"

**With attached:** Annotated profile image showing issues and fixes.

## Deployment

- **Local:** `python3 batch_processor.py --profiles-file profiles.txt`
- **Docker:** `docker-compose up`
- **Cloud Run:** `./deploy-cloud-run.sh`
- **Scheduled:** Use `scheduler.py` or cron

See `ARCHITECTURE.md` for complete details.

