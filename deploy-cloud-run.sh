#!/bin/bash
# Deploy LinkedIn Outreach Automation to Google Cloud Run

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "Google Cloud Run Deployment"
echo "=========================================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${YELLOW}No project set. Please set your project:${NC}"
    echo "  gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo -e "${GREEN}Project: ${PROJECT_ID}${NC}"

# Region
REGION=${REGION:-us-central1}
echo -e "${GREEN}Region: ${REGION}${NC}"

# Service name
SERVICE_NAME="linkedin-outreach"
echo -e "${GREEN}Service: ${SERVICE_NAME}${NC}"

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Build and deploy
echo -e "\n${GREEN}Building and deploying to Cloud Run...${NC}"

# Build the image
echo "Building Docker image..."
gcloud builds submit --tag gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest \
  --platform managed \
  --region ${REGION} \
  --memory 4Gi \
  --cpu 2 \
  --timeout 3600 \
  --max-instances 1 \
  --min-instances 0 \
  --allow-unauthenticated \
  --set-env-vars "ANNOTATION_BACKEND=gemini_native_pro" \
  --set-secrets "APIFY_API_KEY=apify-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest,OPENAI_API_KEY=openai-api-key:latest"

echo -e "\n${GREEN}Deployment complete!${NC}"
echo ""
echo "Service URL:"
gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)'
echo ""
echo "To view logs:"
echo "  gcloud run logs read ${SERVICE_NAME} --region ${REGION}"
echo ""
echo "To trigger manually:"
echo "  curl -X POST \$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')/run"

