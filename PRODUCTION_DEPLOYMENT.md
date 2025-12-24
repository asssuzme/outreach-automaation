# Production Deployment Guide

Complete guide for deploying LinkedIn Outreach Automation to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Docker)](#quick-start-docker)
3. [Cloud Deployment Options](#cloud-deployment-options)
4. [Scheduling](#scheduling)
5. [Monitoring & Logging](#monitoring--logging)
6. [Security Best Practices](#security-best-practices)
7. [Scaling & Performance](#scaling--performance)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Python 3.9+**
- **Docker** (for containerized deployment)
- **API Keys:**
  - Apify API key
  - Google Gemini API key
  - OpenAI API key (optional)
- **LinkedIn Cookies** (`linkedin_cookies.json`)
- **Server/VPS** (for cloud deployment)

---

## Quick Start (Docker)

### 1. Setup Environment

```bash
# Clone repository
git clone <your-repo>
cd outreach-automation

# Create .env file
cp .env.example .env
# Edit .env with your API keys
```

### 2. Deploy

```bash
# Make deploy script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

### 3. Run Batch Processing

```bash
# Run manually
docker-compose exec outreach-automation python3 batch_processor.py \
  --profiles-file profiles_batch.txt

# Or run from host
docker-compose exec outreach-automation python3 batch_processor.py \
  --profiles-file profiles_batch.txt
```

---

## Cloud Deployment Options

### Option 1: DigitalOcean Droplet (Recommended)

**Pros:** Simple, affordable, full control  
**Cost:** ~$12-24/month

```bash
# 1. Create Ubuntu 22.04 droplet (2GB RAM minimum)
# 2. SSH into droplet
ssh root@your-droplet-ip

# 3. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 4. Install Docker Compose
apt-get install docker-compose

# 5. Clone and deploy
git clone <your-repo>
cd outreach-automation
./deploy.sh
```

### Option 2: AWS EC2

**Pros:** Scalable, integrates with AWS services  
**Cost:** ~$15-30/month

```bash
# 1. Launch EC2 instance (t3.medium recommended)
# 2. Security Group: Allow SSH (port 22)
# 3. Install Docker (same as DigitalOcean)
# 4. Deploy using deploy.sh
```

### Option 3: Google Cloud Run (Serverless)

**Pros:** Pay-per-use, auto-scaling  
**Cost:** Pay only when running

```bash
# 1. Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/linkedin-outreach

# 2. Deploy to Cloud Run
gcloud run deploy linkedin-outreach \
  --image gcr.io/PROJECT_ID/linkedin-outreach \
  --platform managed \
  --memory 4Gi \
  --timeout 3600
```

### Option 4: AWS Lambda + ECS Fargate

**Pros:** Fully serverless, event-driven  
**Cost:** Pay-per-execution

```yaml
# Use AWS EventBridge to trigger ECS Fargate task
# Schedule: cron(0 9 * * ? *)  # Daily at 9 AM
```

---

## Scheduling

### Method 1: Cron (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Run daily at 9 AM
0 9 * * * cd /path/to/outreach-automation && docker-compose exec -T outreach-automation python3 batch_processor.py --profiles-file profiles_batch.txt >> logs/cron.log 2>&1

# Run weekly on Mondays at 10 AM
0 10 * * 1 cd /path/to/outreach-automation && docker-compose exec -T outreach-automation python3 batch_processor.py --profiles-file profiles_batch.txt >> logs/cron.log 2>&1
```

### Method 2: Python Scheduler

```bash
# Install schedule library
pip install schedule

# Run scheduler
python3 scheduler.py --schedule daily --time "09:00" --profiles-file profiles_batch.txt

# Or run immediately
python3 scheduler.py --run-now --profiles-file profiles_batch.txt
```

### Method 3: Systemd Timer (Linux)

Create `/etc/systemd/system/linkedin-outreach.service`:

```ini
[Unit]
Description=LinkedIn Outreach Automation
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
WorkingDirectory=/path/to/outreach-automation
ExecStart=/usr/bin/docker-compose exec -T outreach-automation python3 batch_processor.py --profiles-file profiles_batch.txt
StandardOutput=append:/path/to/outreach-automation/logs/systemd.log
StandardError=append:/path/to/outreach-automation/logs/systemd.log
```

Create `/etc/systemd/system/linkedin-outreach.timer`:

```ini
[Unit]
Description=Run LinkedIn Outreach Daily
Requires=linkedin-outreach.service

[Timer]
OnCalendar=daily
OnCalendar=09:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:

```bash
systemctl enable linkedin-outreach.timer
systemctl start linkedin-outreach.timer
systemctl status linkedin-outreach.timer
```

---

## Monitoring & Logging

### Log Files

All logs are stored in `logs/` directory:

- `scheduler_YYYYMMDD.log` - Scheduler logs
- `batch_results_YYYYMMDD_HHMMSS.json` - Batch processing results
- `batch_processing.log` - Real-time batch processing output

### Monitoring Script

Create `monitor.py`:

```python
#!/usr/bin/env python3
import json
import glob
from pathlib import Path

# Check latest batch results
results_files = sorted(glob.glob("logs/batch_results_*.json"))
if results_files:
    with open(results_files[-1]) as f:
        result = json.load(f)
    print(f"Last batch: {result['processed']} processed, {result['succeeded']} succeeded")
```

### Health Checks

```bash
# Check if container is running
docker ps | grep linkedin-outreach

# Check logs
docker-compose logs -f outreach-automation

# Check disk space
df -h

# Check API quota (add to monitor.py)
```

### Alerting (Optional)

Set up email/Slack alerts for failures:

```python
# Add to batch_processor.py
def send_alert(message):
    import smtplib
    # Send email or Slack webhook
    pass
```

---

## Security Best Practices

### 1. Environment Variables

**Never commit API keys!**

```bash
# .env file (add to .gitignore)
APIFY_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

### 2. Secrets Management

**Option A: Docker Secrets**
```bash
echo "your_api_key" | docker secret create apify_key -
```

**Option B: AWS Secrets Manager**
```python
import boto3
secrets = boto3.client('secretsmanager')
api_key = secrets.get_secret_value(SecretId='apify-key')['SecretString']
```

**Option C: HashiCorp Vault**
```python
import hvac
client = hvac.Client(url='https://vault.example.com')
api_key = client.secrets.kv.v2.read_secret_version(path='apify-key')['data']['data']['key']
```

### 3. File Permissions

```bash
# Restrict cookie file access
chmod 600 linkedin_cookies.json

# Restrict .env file
chmod 600 .env
```

### 4. Network Security

- Use VPN/proxy for LinkedIn access
- Rate limit requests (already built-in)
- Rotate LinkedIn cookies regularly

### 5. Container Security

```dockerfile
# Run as non-root user (already in Dockerfile)
USER appuser

# Use minimal base image
FROM python:3.9-slim
```

---

## Scaling & Performance

### Horizontal Scaling

Run multiple instances for different profile batches:

```bash
# Instance 1: Batch A
docker-compose -f docker-compose.yml -p batch-a up -d

# Instance 2: Batch B  
docker-compose -f docker-compose.yml -p batch-b up -d
```

### Vertical Scaling

Increase resources in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '4'      # Increase from 2
      memory: 8G     # Increase from 4G
```

### Performance Optimization

1. **Parallel Processing:** Process multiple profiles simultaneously (requires code changes)
2. **Caching:** Cache API responses to reduce API calls
3. **Batch API Calls:** Group API requests where possible
4. **Database:** Store results in database instead of JSON files

---

## Troubleshooting

### Common Issues

#### 1. Docker Container Won't Start

```bash
# Check logs
docker-compose logs outreach-automation

# Check if ports are in use
netstat -tulpn | grep :80

# Rebuild image
docker-compose build --no-cache
```

#### 2. Chrome/Selenium Errors

```bash
# Update ChromeDriver
pip install --upgrade undetected-chromedriver

# Check Chrome version
google-chrome --version
```

#### 3. API Rate Limits

- Increase delays in `batch_processor.py`
- Use API key rotation
- Implement exponential backoff

#### 4. LinkedIn Cookie Expired

```bash
# Re-export cookies from browser
# Update linkedin_cookies.json
```

#### 5. Out of Memory

```bash
# Increase Docker memory limit
# Or process fewer profiles per batch
```

### Debug Mode

```bash
# Run with verbose logging
docker-compose exec outreach-automation python3 batch_processor.py \
  --profiles-file profiles_batch.txt \
  --no-send-messages \
  --output debug_results.json
```

---

## Production Checklist

- [ ] API keys configured in `.env`
- [ ] LinkedIn cookies exported and valid
- [ ] Docker image built successfully
- [ ] Container starts without errors
- [ ] Test run completes successfully
- [ ] Scheduling configured (cron/systemd)
- [ ] Logging directory created
- [ ] Monitoring/alerting set up
- [ ] Backup strategy for output data
- [ ] Rate limiting configured
- [ ] Security hardening applied
- [ ] Documentation updated

---

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review `batch_processing.log`
3. Check Docker logs: `docker-compose logs`
4. Review GitHub issues (if applicable)

---

## Cost Estimates

**Monthly Costs (Approximate):**

- **DigitalOcean Droplet:** $12-24/month
- **Apify API:** $49-99/month (depends on usage)
- **Google Gemini API:** Pay-per-use (~$0.01-0.10 per profile)
- **OpenAI API:** Optional, pay-per-use
- **Total:** ~$70-150/month for moderate usage

---

## Next Steps

1. **Test Deployment:** Run test batch with 2-3 profiles
2. **Monitor:** Watch logs for first few runs
3. **Scale:** Gradually increase profile count
4. **Optimize:** Fine-tune delays and resource limits
5. **Automate:** Set up monitoring and alerting

