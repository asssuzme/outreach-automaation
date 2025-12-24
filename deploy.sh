#!/bin/bash
# Production deployment script for LinkedIn Outreach Automation

set -e

echo "=========================================="
echo "LinkedIn Outreach Automation - Deployment"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found. Creating template...${NC}"
    cat > .env << EOF
# API Keys
APIFY_API_KEY=your_apify_key_here
GEMINI_API_KEY=your_gemini_key_here
OPENAI_API_KEY=your_openai_key_here

# Configuration
ANNOTATION_BACKEND=gemini_native_pro
OUTPUT_DIR=./output

# LinkedIn Cookies (path to JSON file)
LINKEDIN_COOKIES_FILE=./linkedin_cookies.json
EOF
    echo -e "${RED}Please edit .env file with your API keys before continuing!${NC}"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check required API keys
if [ -z "$APIFY_API_KEY" ] || [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${RED}Error: APIFY_API_KEY and GEMINI_API_KEY must be set in .env${NC}"
    exit 1
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p output logs

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

# Build Docker image
echo -e "${GREEN}Building Docker image...${NC}"
docker build -t linkedin-outreach:latest .

# Stop existing container if running
if [ "$(docker ps -q -f name=linkedin-outreach)" ]; then
    echo "Stopping existing container..."
    docker stop linkedin-outreach
    docker rm linkedin-outreach
fi

# Start container
echo -e "${GREEN}Starting container...${NC}"
docker-compose up -d

echo -e "${GREEN}Deployment complete!${NC}"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"
echo "To run batch: docker-compose exec outreach-automation python3 batch_processor.py --profiles-file profiles.txt"

