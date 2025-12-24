# LinkedIn Profile Scraper - Phase 1

A Python tool that scrapes LinkedIn profile data using Apify's `apimaestro/linkedin-profile-detail` actor and captures a full-page screenshot of the profile.

## Features

- Scrapes LinkedIn profile data using Apify API
- Captures full-page screenshot of the LinkedIn profile
- Saves both scraped data (JSON) and screenshot (PNG) to the output directory
- Simple command-line interface

## Prerequisites

- Python 3.8 or higher
- Apify API key (provided or get from https://console.apify.com/account/integrations)
- LinkedIn session cookies (required for screenshots - see setup below)

## Installation

1. Clone or download this repository

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Playwright browsers (required for screenshot capture):
   ```bash
   playwright install chromium
   ```

4. Set up LinkedIn cookies (required for screenshots):
   
   LinkedIn requires authentication to view profiles, so you need to provide your session cookies.
   
   **How to extract cookies:**
   
   1. **Log in to LinkedIn** in your browser (Chrome/Firefox/Edge)
   2. **Open Developer Tools:**
      - Chrome/Edge: Press `F12` or `Ctrl+Shift+I` (Windows) / `Cmd+Option+I` (Mac)
      - Firefox: Press `F12` or `Ctrl+Shift+I` (Windows) / `Cmd+Option+I` (Mac)
   3. **Navigate to Cookies:**
      - **Chrome/Edge:** Click "Application" tab → Left sidebar: "Cookies" → `https://www.linkedin.com`
      - **Firefox:** Click "Storage" tab → Left sidebar: "Cookies" → `https://www.linkedin.com`
   4. **Find and copy the `li_at` cookie:**
      - Look for a cookie named `li_at`
      - Copy the entire "Value" column (it's a long string)
   5. **Create cookie file:**
      - Create a file named `linkedin_cookies.json` in the project directory
      - Format:
        ```json
        {
          "li_at": "paste_your_cookie_value_here"
        }
        ```
   
   **Important Notes:**
   - Cookies are stored locally and never committed to git (security)
   - Cookies typically last for several weeks/months
   - If cookies expire, you'll need to extract fresh ones and update the file
   - Use a dedicated LinkedIn account for scraping if possible

5. Set up environment variables (optional):
   - Copy `.env.example` to `.env`
   - Add your Apify API key to `.env` (or it's already configured in `config.py`)

## Usage

Run the script with a LinkedIn profile URL as an argument:

```bash
python3 main.py "https://www.linkedin.com/in/profile-url"
```

### Options

- `--cookies-file PATH`: Specify a custom path to your cookies file (default: `linkedin_cookies.json`)

### Examples

```bash
# Basic usage (uses default linkedin_cookies.json)
python3 main.py "https://www.linkedin.com/in/ashutosh-lath-3a374b2b3"

# With custom cookie file
python3 main.py "https://www.linkedin.com/in/profile-url" --cookies-file /path/to/cookies.json
```

## Output

The script creates two files in the `output/` directory:

1. **Profile Data** (`profile_data_YYYYMMDD_HHMMSS.json`): JSON file containing all scraped profile information
2. **Screenshot** (`screenshot_YYYYMMDD_HHMMSS.png`): Full-page screenshot of the LinkedIn profile

Both files are timestamped to avoid overwriting previous results.

## Project Structure

```
.
├── main.py                  # Main entry point script
├── apify_client.py          # Apify API client wrapper
├── cookie_manager.py        # Cookie management for LinkedIn authentication
├── config.py                # Configuration settings
├── requirements.txt         # Python dependencies
├── .env.example             # Example environment file template
├── linkedin_cookies.json    # LinkedIn session cookies (create this - see setup)
├── .gitignore              # Git ignore rules
├── README.md               # This file
└── output/                 # Output directory (created automatically)
    ├── profile_data_*.json
    └── screenshot_*.png
```

## API Details

- **Apify Actor**: `apimaestro/linkedin-profile-detail`
- **API Endpoint**: `https://api.apify.com/v2/acts/apimaestro~linkedin-profile-detail/run-sync-get`
- **Authentication**: Bearer token (API key)

## Notes

- The script uses Playwright to capture screenshots in headless mode with cookie authentication
- Screenshots are captured as full-page images
- The Apify API call may take some time depending on the profile complexity
- Cookies are automatically loaded from `linkedin_cookies.json` on each run
- Cookies are stored locally and never committed to git for security
- Ensure you comply with LinkedIn's Terms of Service when using this tool

## Troubleshooting

1. **Playwright not installed**: Run `playwright install chromium`

2. **API key error**: Ensure your `.env` file contains a valid `APIFY_API_KEY` or it's configured in `config.py`

3. **Cookie errors:**
   - **"Cookies not found"**: Create `linkedin_cookies.json` file with your LinkedIn `li_at` cookie (see setup instructions)
   - **"Cookies expired"**: Your LinkedIn session expired. Extract fresh cookies from your browser and update `linkedin_cookies.json`
   - **"Authentication failed"**: Cookies are invalid or expired. Check that the `li_at` cookie value is correct

4. **Screenshot shows login page:**
   - Cookies are missing, expired, or invalid
   - Verify `linkedin_cookies.json` exists and contains a valid `li_at` cookie
   - Extract fresh cookies from your browser (see setup instructions)

5. **Timeout errors**: The script has a 5-minute timeout for API calls and 60-second timeout for page loads

6. **LinkedIn blocking access:**
   - LinkedIn may temporarily block automated access
   - Wait a few minutes and try again
   - Ensure cookies are fresh and valid
