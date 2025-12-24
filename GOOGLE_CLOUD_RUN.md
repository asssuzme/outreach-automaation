# Google Cloud Run Deployment Guide

Complete guide for deploying LinkedIn Outreach Automation to Google Cloud Run.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Setup Secrets](#setup-secrets)
4. [Deploy](#deploy)
5. [Schedule Jobs](#schedule-jobs)
6. [Monitor & Debug](#monitor--debug)
7. [Cost Optimization](#cost-optimization)

---

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **gcloud CLI** installed: https://cloud.google.com/sdk/docs/install
3. **Docker** installed (for local testing)
4. **API Keys:**
   - Apify API key
   - Google Gemini API key
   - OpenAI API key (optional)

---

## Quick Start

### 1. Initialize Google Cloud

```bash
# Login to Google Cloud
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### 2. Setup Secrets

Store your API keys securely:

```bash
# Create secrets
echo -n "your_apify_key" | gcloud secrets create apify-api-key --data-file=-
echo -n "your_gemini_key" | gcloud secrets create gemini-api-key --data-file=-
echo -n "your_openai_key" | gcloud secrets create openai-api-key --data-file=-

# Grant Cloud Run access to secrets
gcloud secrets add-iam-policy-binding apify-api-key \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 3. Deploy

```bash
# Make script executable
chmod +x deploy-cloud-run.sh

# Deploy
./deploy-cloud-run.sh
```

Or manually:

```bash
# Build and push image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/linkedin-outreach

# Deploy to Cloud Run
gcloud run deploy linkedin-outreach \
  --image gcr.io/YOUR_PROJECT_ID/linkedin-outreach:latest \
  --platform managed \
  --region us-central1 \
  --memory 4Gi \
  --cpu 2 \
  --timeout 3600 \
  --max-instances 1 \
  --set-secrets "APIFY_API_KEY=apify-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest"
```

---

## Setup Secrets

### Option 1: Secret Manager (Recommended)

```bash
# Create secrets
gcloud secrets create apify-api-key --replication-policy="automatic"
gcloud secrets create gemini-api-key --replication-policy="automatic"
gcloud secrets create openai-api-key --replication-policy="automatic"

# Add secret versions
echo -n "your_apify_key" | gcloud secrets versions add apify-api-key --data-file=-
echo -n "your_gemini_key" | gcloud secrets versions add gemini-api-key --data-file=-
echo -n "your_openai_key" | gcloud secrets versions add openai-api-key --data-file=-

# Get service account email
SERVICE_ACCOUNT=$(gcloud run services describe linkedin-outreach \
  --region us-central1 \
  --format 'value(spec.template.spec.serviceAccountName)')

# Grant access
gcloud secrets add-iam-policy-binding apify-api-key \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

### Option 2: Environment Variables (Less Secure)

```bash
gcloud run deploy linkedin-outreach \
  --set-env-vars "APIFY_API_KEY=your_key,GEMINI_API_KEY=your_key"
```

---

## Deploy

### Method 1: Using Deployment Script

```bash
./deploy-cloud-run.sh
```

### Method 2: Using Cloud Build

```bash
# Submit build
gcloud builds submit --config cloudbuild.yaml
```

### Method 3: Manual Deployment

```bash
# Build image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/linkedin-outreach

# Deploy
gcloud run deploy linkedin-outreach \
  --image gcr.io/YOUR_PROJECT_ID/linkedin-outreach:latest \
  --platform managed \
  --region us-central1 \
  --memory 4Gi \
  --cpu 2 \
  --timeout 3600 \
  --max-instances 1 \
  --min-instances 0 \
  --set-secrets "APIFY_API_KEY=apify-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest"
```

### Configuration Options

- **Memory:** `4Gi` (required for Chrome/Selenium)
- **CPU:** `2` (recommended for faster processing)
- **Timeout:** `3600` seconds (1 hour max for Cloud Run)
- **Max Instances:** `1` (prevents parallel runs)
- **Min Instances:** `0` (scale to zero when not in use)

---

## Schedule Jobs

### Using Cloud Scheduler

Create a scheduled job that triggers Cloud Run:

```bash
# Get Cloud Run service URL
SERVICE_URL=$(gcloud run services describe linkedin-outreach \
  --region us-central1 \
  --format 'value(status.url)')

# Create scheduler job (daily at 9 AM UTC)
gcloud scheduler jobs create http linkedin-outreach-daily \
  --location us-central1 \
  --schedule "0 9 * * *" \
  --uri "${SERVICE_URL}/run" \
  --http-method POST \
  --message-body '{
    "profiles": [
      "https://www.linkedin.com/in/profile1",
      "https://www.linkedin.com/in/profile2"
    ],
    "send_messages": true
  }' \
  --headers "Content-Type=application/json" \
  --time-zone "UTC"
```

### Using Profiles File in Cloud Storage

1. **Upload profiles file to Cloud Storage:**

```bash
# Create bucket
gsutil mb gs://your-project-profiles

# Upload profiles file
gsutil cp profiles_batch.txt gs://your-project-profiles/
```

2. **Create scheduled job:**

```bash
gcloud scheduler jobs create http linkedin-outreach-daily \
  --location us-central1 \
  --schedule "0 9 * * *" \
  --uri "${SERVICE_URL}/run-file" \
  --http-method POST \
  --message-body '{
    "profiles_file": "gs://your-project-profiles/profiles_batch.txt",
    "send_messages": true
  }' \
  --headers "Content-Type=application/json"
```

### Manual Trigger

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe linkedin-outreach \
  --region us-central1 \
  --format 'value(status.url)')

# Trigger manually
curl -X POST "${SERVICE_URL}/run" \
  -H "Content-Type: application/json" \
  -d '{
    "profiles": ["https://www.linkedin.com/in/profile1"],
    "send_messages": true
  }'
```

---

## Monitor & Debug

### View Logs

```bash
# Real-time logs
gcloud run logs tail linkedin-outreach --region us-central1

# Recent logs
gcloud run logs read linkedin-outreach --region us-central1 --limit 50
```

### Check Service Status

```bash
# Service details
gcloud run services describe linkedin-outreach --region us-central1

# List revisions
gcloud run revisions list --service linkedin-outreach --region us-central1
```

### Debug Failed Jobs

```bash
# View execution logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=linkedin-outreach" \
  --limit 50 \
  --format json
```

### Test Locally

```bash
# Build Docker image locally
docker build -f Dockerfile.cloudrun -t linkedin-outreach:local .

# Run locally
docker run -p 8080:8080 \
  -e APIFY_API_KEY=your_key \
  -e GEMINI_API_KEY=your_key \
  linkedin-outreach:local

# Test endpoint
curl -X POST http://localhost:8080/run \
  -H "Content-Type: application/json" \
  -d '{"profiles": ["https://www.linkedin.com/in/test"], "send_messages": false}'
```

---

## Cost Optimization

### Cloud Run Pricing

- **CPU:** $0.00002400 per vCPU-second
- **Memory:** $0.00000250 per GiB-second
- **Requests:** $0.40 per million requests
- **Free Tier:** 2 million requests/month, 360,000 GiB-seconds/month

### Optimization Tips

1. **Scale to Zero:** Set `--min-instances 0` (default)
2. **Increase Timeout:** Use full 3600 seconds to avoid multiple invocations
3. **Batch Processing:** Process multiple profiles in one request
4. **Memory:** Use 4Gi minimum (required for Chrome)
5. **CPU:** Use 2 CPUs for faster processing (reduces billable time)

### Estimated Costs

**Example:** Processing 10 profiles daily
- **Execution time:** ~30 minutes per batch
- **Memory:** 4Gi × 1800 seconds = 7,200 GiB-seconds
- **CPU:** 2 vCPU × 1800 seconds = 3,600 vCPU-seconds
- **Daily cost:** ~$0.10
- **Monthly cost:** ~$3.00

---

## Troubleshooting

### Common Issues

#### 1. Timeout Errors

**Problem:** Job times out before completion

**Solution:**
- Increase timeout: `--timeout 3600`
- Process fewer profiles per batch
- Optimize code for faster execution

#### 2. Memory Errors

**Problem:** Container runs out of memory

**Solution:**
- Increase memory: `--memory 8Gi`
- Process profiles sequentially
- Clear browser cache between profiles

#### 3. Chrome/Selenium Errors

**Problem:** Chrome fails to start in Cloud Run

**Solution:**
- Ensure Chrome is installed in Dockerfile
- Use headless mode
- Set `DISPLAY=:99` environment variable

#### 4. Secret Access Errors

**Problem:** Cannot access secrets

**Solution:**
```bash
# Grant service account access
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/secretmanager.secretAccessor"
```

#### 5. LinkedIn Cookie Expired

**Problem:** LinkedIn authentication fails

**Solution:**
- Update `linkedin_cookies.json` in Cloud Storage
- Re-export cookies from browser
- Use Secret Manager for cookies

---

## Advanced Configuration

### Custom Domain

```bash
# Map custom domain
gcloud run domain-mappings create \
  --service linkedin-outreach \
  --domain api.yourdomain.com \
  --region us-central1
```

### VPC Connector (if needed)

```bash
# Create VPC connector
gcloud compute networks vpc-access connectors create connector-name \
  --region us-central1 \
  --network default \
  --range 10.8.0.0/28

# Deploy with VPC connector
gcloud run deploy linkedin-outreach \
  --vpc-connector connector-name \
  --vpc-egress all-traffic
```

### Cloud Storage for Output

Modify `cloud-run-handler.py` to upload results to Cloud Storage:

```python
from google.cloud import storage

def upload_results(result):
    client = storage.Client()
    bucket = client.bucket('your-output-bucket')
    blob = bucket.blob(f'results/{datetime.now().isoformat()}.json')
    blob.upload_from_string(json.dumps(result))
```

---

## Production Checklist

- [ ] Google Cloud project created
- [ ] Billing enabled
- [ ] Required APIs enabled
- [ ] Secrets created in Secret Manager
- [ ] Service account has secret access
- [ ] Docker image builds successfully
- [ ] Cloud Run service deployed
- [ ] Health check endpoint works
- [ ] Test run completes successfully
- [ ] Cloud Scheduler job created
- [ ] Monitoring alerts configured
- [ ] Cost alerts set up

---

## Next Steps

1. **Deploy:** Run `./deploy-cloud-run.sh`
2. **Test:** Trigger manual run via curl
3. **Schedule:** Create Cloud Scheduler job
4. **Monitor:** Set up Cloud Monitoring alerts
5. **Optimize:** Fine-tune memory/CPU based on usage

---

## Support

For issues:
- Check Cloud Run logs: `gcloud run logs read`
- Review Cloud Build logs: `gcloud builds list`
- Check Secret Manager: `gcloud secrets list`
- Review Cloud Scheduler: `gcloud scheduler jobs list`

