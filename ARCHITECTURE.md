# LinkedIn Outreach Automation - Complete Architecture

## Overview

**Complete end-to-end system** that scrapes LinkedIn profiles, analyzes them with AI, generates annotated visual critiques, and automatically sends personalized outreach messages via LinkedIn.

**Full Pipeline:** LinkedIn Profile URL → Scrape → Screenshot → Annotate → Generate Message → **Send LinkedIn Message**

---

## Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PHASE 1: DATA COLLECTION                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   LinkedIn Profile URL                                                   │
│        ↓                                                                 │
│   [Apify API] ──→ Profile Data (JSON)                                   │
│        ↓                                                                 │
│   [Apify API] ──→ Posts Data (JSON)                                      │
│        ↓                                                                 │
│   [Selenium + Chrome] ──→ Profile Screenshot (PNG)                      │
│        ↓                                                                 │
│   [Selenium + Chrome] ──→ Post Screenshots (PNG)                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    PHASE 2: AI ANNOTATION                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Screenshots (Profile + Posts)                                          │
│        ↓                                                                 │
│   [Google Gemini API] ──→ Visual Analysis + Annotations                 │
│        ↓                                                                 │
│   Annotated Images (with red circles, arrows, callouts)                  │
│        ↓                                                                 │
│   [Email Generator] ──→ Outreach Email (HTML)                            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    PHASE 3: LINKEDIN MESSAGING                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Annotated Images + Profile Data                                        │
│        ↓                                                                 │
│   [Message Generator] ──→ Personalized LinkedIn Message                  │
│        ↓                                                                 │
│   [Selenium Automation] ──→ Login to LinkedIn                           │
│        ↓                                                                 │
│   [Selenium Automation] ──→ Navigate to Profile                        │
│        ↓                                                                 │
│   [Selenium Automation] ──→ Open Message Dialog                        │
│        ↓                                                                 │
│   [Selenium Automation] ──→ Type Message + Attach Images               │
│        ↓                                                                 │
│   [Selenium Automation] ──→ Click Send                                  │
│        ↓                                                                 │
│   [Selenium Automation] ──→ Handle Confirmation Popup                  │
│        ↓                                                                 │
│   ✅ LinkedIn Message Sent                                               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Complete Workflow Steps

### Step 1: Profile Scraping (Apify)
- **Input:** LinkedIn profile URL
- **Service:** Apify API (`apimaestro/linkedin-profile-detail`)
- **Output:** `profile_data.json` (name, headline, experience, education, etc.)

### Step 2: Posts Scraping (Apify)
- **Input:** LinkedIn profile URL
- **Service:** Apify API (`apimaestro/linkedin-profile-posts`)
- **Output:** `posts.json` (all posts with text, engagement, dates)

### Step 3: Screenshot Capture (Selenium)
- **Input:** LinkedIn profile URL + cookies
- **Service:** Selenium + undetected-chromedriver + Chrome
- **Output:** 
  - `screenshot.png` (full profile page)
  - `post_screenshots/post_*.png` (individual post screenshots)

### Step 4: AI Annotation (Google Gemini)
- **Input:** Screenshots
- **Service:** Google Gemini API (`gemini-3-pro-image-preview`)
- **Process:** 
  - Sends screenshot to Gemini with detailed prompt
  - Gemini analyzes profile from marketing perspective
  - Returns annotated image with red circles, arrows, callouts
- **Output:** `nano_banana_annotated/profile.png` (annotated image)

### Step 5: Email Generation (Optional)
- **Input:** Annotated images + profile data
- **Service:** OpenAI GPT / Local generation
- **Output:** `outreach_email_nano.html` (HTML email template)

### Step 6: LinkedIn Message Sending (Selenium)
- **Input:** Profile URL + Message + Annotated Images
- **Service:** Selenium automation
- **Process:**
  1. Login using LinkedIn cookies
  2. Navigate to target profile
  3. Click "Message" button (or "More" → "Message" for InMail)
  4. Type personalized message
  5. Attach annotated images via file input
  6. Click "Send" button
  7. Handle confirmation popup (click Send again)
  8. Verify message sent
- **Output:** ✅ Message sent to LinkedIn profile

---

## Batch Processing Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BATCH PROCESSOR                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Input: profiles_batch.txt (one URL per line)                          │
│        ↓                                                                 │
│   For each profile:                                                      │
│        ├─→ Scrape Profile Data                                          │
│        ├─→ Scrape Posts Data                                            │
│        ├─→ Capture Screenshots                                          │
│        ├─→ Annotate with Gemini                                         │
│        ├─→ Generate Email                                               │
│        └─→ Send LinkedIn Message (with delay)                            │
│                                                                          │
│   Output:                                                                │
│   - output/{profile_id}/ (all data)                                     │
│   - batch_results.json (processing summary)                             │
│   - LinkedIn messages sent automatically                                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Key Components

### 1. Data Collection (`main.py`, `apify_client.py`)
- **Apify Client:** Wraps Apify API for profile/post scraping
- **Screenshot Capture:** Selenium-based screenshot capture with high DPI
- **Cookie Management:** LinkedIn session cookies for authentication

### 2. AI Annotation (`nano_banana_annotator.py`)
- **Backend Options:**
  - `gemini_native_pro`: Google Gemini 3 Pro Image Preview (4K, best quality)
  - `gemini_native`: Google Gemini 2.5 Flash Image (1024px, faster)
  - `gemini_hybrid`: Gemini text analysis + PIL rendering (fallback)
  - `kie`: KIE.ai Nano Banana Pro (paid alternative)
- **Prompt Engineering:** Detailed prompts to preserve base image quality
- **Output:** Annotated PNG images with transparent overlays

### 3. Message Generation (`send_with_photos.py`, `batch_processor.py`)
- **Message Template:** Professional agency-focused message
- **Personalization:** Uses profile first name
- **Image Attachment:** Attaches annotated profile image

### 4. LinkedIn Automation (`send_with_photos.py`)
- **Browser:** undetected-chromedriver (bypasses detection)
- **Login:** Cookie-based authentication
- **Message Dialog:** Handles both direct messages and InMail
- **File Upload:** Selenium file input for image attachment
- **Confirmation Handling:** Automatically handles LinkedIn's confirmation popup

### 5. Batch Processing (`batch_processor.py`)
- **Multi-Profile:** Processes multiple profiles sequentially
- **Error Handling:** Continues if one profile fails
- **Rate Limiting:** Built-in delays between profiles/messages
- **Progress Tracking:** JSON results with success/failure status

---

## File Structure

```
outreach-automation/
├── main.py                      # Main orchestrator (scrape + screenshot)
├── batch_processor.py           # Batch processing for multiple profiles
├── send_with_photos.py          # LinkedIn message sending automation
├── nano_banana_annotator.py     # AI annotation engine (Gemini)
├── config.py                    # API keys and configuration
├── 
├── ─── DATA COLLECTION ───
├── apify_client.py              # Apify API wrapper
├── cookie_manager.py            # LinkedIn cookie management
├── linkedin_cookies.json        # Stored LinkedIn session cookies
├── 
├── ─── ANNOTATION ───
├── nano_banana_annotator.py     # Gemini-based annotation
├── generate_email_nano.py       # Email generation from annotations
├── 
├── ─── DEPLOYMENT ───
├── Dockerfile                   # Docker container for production
├── Dockerfile.cloudrun          # Google Cloud Run optimized
├── docker-compose.yml           # Docker Compose configuration
├── deploy.sh                   # Deployment script
├── deploy-cloud-run.sh          # Cloud Run deployment script
├── cloud-run-handler.py         # HTTP handler for Cloud Run
├── scheduler.py                 # Python scheduler for cron jobs
├── 
├── ─── DOCUMENTATION ───
├── ARCHITECTURE.md              # This file
├── PRODUCTION_DEPLOYMENT.md     # Production deployment guide
├── GOOGLE_CLOUD_RUN.md         # Cloud Run specific guide
├── BATCH_PROCESSING.md         # Batch processing guide
├── README.md                    # Main README
├── 
└── output/
    └── {profile_id}/
        ├── profile_data.json           # Scraped profile data
        ├── posts.json                 # Scraped posts data
        ├── posts_analysis.json        # Posts categorization
        ├── screenshot.png             # Profile screenshot
        ├── post_screenshots/          # Post screenshots
        │   └── post_*.png
        ├── nano_banana_annotated/     # AI-annotated images
        │   ├── profile.png            # Annotated profile
        │   └── post_*.png             # Annotated posts
        └── outreach_email_nano.html   # Generated email
```

---

## API Services Used

| Service | Purpose | Model/Endpoint |
|---------|---------|----------------|
| **Apify** | LinkedIn scraping | `apimaestro/linkedin-profile-detail`<br>`apimaestro/linkedin-profile-posts` |
| **Google Gemini** | Image annotation | `gemini-3-pro-image-preview` (Pro)<br>`gemini-2.5-flash-image` (Fast) |
| **OpenAI** | Email generation (optional) | `gpt-3.5-turbo` |
| **Selenium** | Browser automation | Chrome + undetected-chromedriver |

---

## Message Template

**Current Message Format:**

```
Hey {first_name}! 👋

I run a personal branding agency, and I personally took some time to do a complete breakdown of your LinkedIn profile. 

I've attached an annotated snapshot that shows exactly where your profile is losing people and what specific fixes would make the biggest impact.

I'd love to discuss this further with you - happy to hop on a quick call to walk you through the full breakdown and answer any questions. Would that be helpful?
```

**Attachments:**
- Annotated profile image (`nano_banana_annotated/profile.png`)
- Optionally: First annotated post image

---

## Complete Data Flow

```
LinkedIn Profile URL
    ↓
[main.py]
    ├─→ [Apify] → profile_data.json
    ├─→ [Apify] → posts.json
    ├─→ [Selenium] → screenshot.png
    └─→ [Selenium] → post_screenshots/*.png
    ↓
[nano_banana_annotator.py]
    ├─→ [Gemini API] → Annotated profile.png
    └─→ [Gemini API] → Annotated post_*.png
    ↓
[generate_email_nano.py]
    └─→ outreach_email_nano.html
    ↓
[send_with_photos.py]
    ├─→ [Selenium] → Login to LinkedIn
    ├─→ [Selenium] → Navigate to profile
    ├─→ [Selenium] → Open message dialog
    ├─→ [Selenium] → Type message
    ├─→ [Selenium] → Attach images
    ├─→ [Selenium] → Click Send
    └─→ [Selenium] → Handle confirmation popup
    ↓
✅ LinkedIn Message Sent
```

---

## Batch Processing Flow

```
profiles_batch.txt
    ↓
[batch_processor.py]
    ↓
For each profile URL:
    ├─→ Process Profile (Steps 1-5 above)
    ├─→ Wait 30 seconds (rate limiting)
    ├─→ Send LinkedIn Message
    └─→ Wait 60 seconds (LinkedIn rate limiting)
    ↓
batch_results.json
    ├─→ Total processed
    ├─→ Succeeded
    ├─→ Failed
    └─→ Messages sent
```

---

## Configuration

### Environment Variables (`.env`)

```bash
# Apify API
APIFY_API_KEY=your_apify_key

# Google Gemini API
GEMINI_API_KEY=your_gemini_key

# OpenAI API (optional)
OPENAI_API_KEY=your_openai_key

# Annotation Backend
ANNOTATION_BACKEND=gemini_native_pro

# Output Directory
OUTPUT_DIR=./output
```

### LinkedIn Cookies (`linkedin_cookies.json`)

```json
{
  "li_at": "your_linkedin_session_cookie",
  "JSESSIONID": "your_jsession_id"
}
```

---

## Usage Examples

### Single Profile (Full Pipeline)

```bash
# Process single profile and send message
python3 main.py https://www.linkedin.com/in/username
python3 send_with_photos.py --profile-dir output/username
```

### Batch Processing

```bash
# Process multiple profiles and send messages automatically
python3 batch_processor.py --profiles-file profiles_batch.txt
```

### Manual Message Sending

```bash
# Send message to specific profile
python3 send_with_photos.py \
  --profile-dir output/username \
  --profile-url https://www.linkedin.com/in/username
```

---

## Deployment Options

### 1. Local Development
```bash
python3 batch_processor.py --profiles-file profiles.txt
```

### 2. Docker
```bash
docker-compose up
```

### 3. Google Cloud Run
```bash
./deploy-cloud-run.sh
```

### 4. Scheduled (Cron)
```bash
# Daily at 9 AM
0 9 * * * cd /path/to/outreach-automation && python3 batch_processor.py --profiles-file profiles.txt
```

---

## Key Features

✅ **Complete Automation:** End-to-end from URL to sent message  
✅ **AI-Powered Analysis:** Google Gemini visual annotation  
✅ **Batch Processing:** Handle multiple profiles automatically  
✅ **Error Handling:** Continues processing if one profile fails  
✅ **Rate Limiting:** Built-in delays to avoid API limits  
✅ **Production Ready:** Docker, Cloud Run, scheduling support  
✅ **Professional Messages:** Agency-focused outreach template  

---

## Success Metrics

- **Profile Processing:** ~5-10 minutes per profile
- **Annotation Quality:** Crystal-clear base image with transparent overlays
- **Message Delivery:** Automatic handling of LinkedIn confirmation popups
- **Batch Efficiency:** Processes 10 profiles in ~1-2 hours
- **Success Rate:** Continues processing even if individual profiles fail

---

## Version History

| Version | Date | Key Features |
|---------|------|--------------|
| V1.0 | Dec 2024 | Initial OCR-based annotation system |
| V2.0 | Dec 2024 | Gemini vision-based annotation |
| **V3.0** | Dec 2024 | **Complete LinkedIn messaging automation** |
| **V3.1** | Dec 2024 | **Batch processing + Cloud Run deployment** |

---

## Architecture Highlights

1. **Modular Design:** Each phase is independent and can be run separately
2. **Multiple Backends:** Support for different annotation engines
3. **Production Ready:** Docker, Cloud Run, scheduling, monitoring
4. **Error Resilient:** Continues processing even if steps fail
5. **Scalable:** Batch processing handles multiple profiles efficiently
6. **Complete Automation:** No manual intervention needed after setup

---

## Next Steps

- **Scale:** Process hundreds of profiles daily
- **Optimize:** Fine-tune delays and resource usage
- **Monitor:** Track success rates and message responses
- **Iterate:** Improve message templates based on responses
