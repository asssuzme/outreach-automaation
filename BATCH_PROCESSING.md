# Batch Processing Guide

## Overview

The batch processor automates the full LinkedIn outreach pipeline for multiple profiles:

1. **Scrape** profile data (Apify)
2. **Scrape** posts data (Apify)  
3. **Capture** screenshots (profile + posts)
4. **Annotate** screenshots (Nano Banana / Gemini)
5. **Generate** outreach email
6. **Send** LinkedIn message (optional)

## Quick Start

### 1. Create a profiles file

Create a text file with LinkedIn profile URLs (one per line):

```bash
# profiles.txt
https://www.linkedin.com/in/profile1
https://www.linkedin.com/in/profile2
profile-username-3
```

### 2. Process profiles

```bash
# Process all profiles (no messages sent)
python3 batch_processor.py --profiles-file profiles.txt

# Process and send messages
python3 batch_processor.py --profiles-file profiles.txt --send-messages

# Process from command line
python3 batch_processor.py --profiles "url1,url2,url3"
```

## Command Line Options

### Required (one of):
- `--profiles-file PATH` - Path to text file with profile URLs
- `--profiles "url1,url2,url3"` - Comma-separated list of URLs

### Optional:
- `--send-messages` - Send LinkedIn messages after processing
- `--skip-scraping` - Skip scraping (use existing data)
- `--skip-annotation` - Skip annotation step
- `--skip-screenshot` - Skip screenshot capture
- `--delay-profiles SECONDS` - Wait time between profiles (default: 30)
- `--delay-messages SECONDS` - Wait time between messages (default: 60)
- `--output PATH` - Save batch results to JSON file

## Examples

### Example 1: Process profiles without sending messages
```bash
python3 batch_processor.py --profiles-file profiles.txt
```

### Example 2: Process and send messages
```bash
python3 batch_processor.py --profiles-file profiles.txt --send-messages
```

### Example 3: Re-annotate existing profiles
```bash
python3 batch_processor.py --profiles-file profiles.txt --skip-scraping --skip-screenshot
```

### Example 4: Process with custom delays
```bash
python3 batch_processor.py \
  --profiles-file profiles.txt \
  --send-messages \
  --delay-profiles 60 \
  --delay-messages 120
```

### Example 5: Save results to file
```bash
python3 batch_processor.py \
  --profiles-file profiles.txt \
  --output batch_results.json
```

## Profile URL Formats

The processor accepts various URL formats:

- Full URL: `https://www.linkedin.com/in/username`
- Short URL: `www.linkedin.com/in/username`
- Username only: `username` (will be converted to full URL)
- With query params: `https://www.linkedin.com/in/username?utm_source=...`

## Output Structure

Each profile is processed into its own directory:

```
output/
├── profile1/
│   ├── profile_data.json
│   ├── posts.json
│   ├── screenshot.png
│   ├── nano_banana_annotated/
│   │   └── profile.png
│   └── ...
├── profile2/
│   └── ...
```

## Batch Results

When using `--output`, you get a JSON file with:

```json
{
  "total_profiles": 5,
  "processed": 5,
  "succeeded": 4,
  "failed": 1,
  "messages_sent": 4,
  "started_at": "2024-01-01T10:00:00",
  "completed_at": "2024-01-01T11:30:00",
  "results": [
    {
      "profile_url": "...",
      "profile_id": "...",
      "status": "completed",
      "steps_completed": [...],
      "errors": [],
      "warnings": []
    }
  ]
}
```

## Error Handling

- If a profile fails, processing continues with the next profile
- Errors are logged in the batch results JSON
- Warnings don't stop processing (e.g., missing posts, annotation failures)

## Rate Limiting

Default delays:
- **30 seconds** between profiles (scraping/screenshots)
- **60 seconds** between messages (LinkedIn)

Adjust with `--delay-profiles` and `--delay-messages` to avoid:
- Apify API rate limits
- LinkedIn rate limits / account restrictions

## Tips

1. **Start small**: Test with 2-3 profiles first
2. **Monitor progress**: Watch the console output
3. **Check results**: Review the output JSON for errors
4. **Resume processing**: Use `--skip-scraping` if you need to re-run annotation
5. **Manual review**: Don't use `--send-messages` until you've verified the output

## Troubleshooting

### Profile scraping fails
- Check Apify API key in `config.py`
- Verify profile URLs are accessible
- Check Apify account credits

### Screenshot capture fails
- Verify LinkedIn cookies in `linkedin_cookies.json`
- Check if profiles are public or require login
- Ensure Chrome/Chromium is installed

### Annotation fails
- Check Google Gemini API key in `config.py`
- Verify API quota/limits
- Check internet connection

### Message sending fails
- Verify LinkedIn cookies are valid
- Check if you're connected to the profile
- Ensure message content is appropriate
- Review browser automation logs

