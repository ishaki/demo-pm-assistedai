#!/bin/bash

# AIHarvest PM System - Production Deployment Script
# This script deploys the application to a test/production server

set -e  # Exit on error

echo "========================================="
echo "AIHarvest PM System - Deployment Script"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Services to deploy. Defaults to the app only -- n8n runs on its own host, so
# bringing it up here would start a second, empty scheduler competing for the
# same webhooks. Override to include it:
#   DEPLOY_SERVICES="backend frontend n8n" ./deploy.sh
SERVICES="${DEPLOY_SERVICES:-backend frontend}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please copy .env.production.example to .env and configure it first:"
    echo "  cp .env.production.example .env"
    echo "  nano .env"
    exit 1
fi

# Source environment variables
set -a
source .env
set +a

echo -e "${GREEN}✓${NC} Environment file loaded"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed!${NC}"
    echo "Please install Docker first. See DEPLOYMENT.md for instructions."
    exit 1
fi

echo -e "${GREEN}✓${NC} Docker is installed"

# Resolve the Compose command. v2 ships as a docker subcommand; fall back to
# the standalone v1 binary for older hosts.
if docker compose version &> /dev/null; then
    DC="docker compose -f docker-compose.prod.yml"
    echo -e "${GREEN}✓${NC} Using Docker Compose v2"
elif command -v docker-compose &> /dev/null; then
    DC="docker-compose -f docker-compose.prod.yml"
    echo -e "${GREEN}✓${NC} Using Docker Compose v1 (standalone)"
else
    echo -e "${RED}Error: Docker Compose is not installed!${NC}"
    echo "Please install Docker Compose first. See DEPLOYMENT.md for instructions."
    exit 1
fi

# Validate required configuration before spending minutes on a build that
# cannot possibly start.
fail=0

if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}✗${NC} DATABASE_URL is not set"
    fail=1
fi

if [ -z "$REACT_APP_API_URL" ]; then
    echo -e "${RED}✗${NC} REACT_APP_API_URL is not set (it is baked into the frontend build)"
    fail=1
fi

if [ -z "$CORS_ORIGINS" ]; then
    echo -e "${RED}✗${NC} CORS_ORIGINS is not set (the browser will be unable to call the API)"
    fail=1
fi

# LLM_PROVIDER must be one of the provider_map keys, and the matching key must
# be present. A mismatch here only surfaces when a user clicks "Get AI
# Decision", long after deployment looks successful.
case "${LLM_PROVIDER:-openai}" in
    claude)
        [ -z "$ANTHROPIC_API_KEY" ] && { echo -e "${RED}✗${NC} LLM_PROVIDER=claude but ANTHROPIC_API_KEY is empty"; fail=1; }
        ;;
    openai)
        [ -z "$OPENAI_API_KEY" ] && { echo -e "${RED}✗${NC} LLM_PROVIDER=openai but OPENAI_API_KEY is empty"; fail=1; }
        ;;
    gemini)
        [ -z "$GOOGLE_API_KEY" ] && { echo -e "${RED}✗${NC} LLM_PROVIDER=gemini but GOOGLE_API_KEY is empty"; fail=1; }
        ;;
    *)
        echo -e "${RED}✗${NC} LLM_PROVIDER='${LLM_PROVIDER}' is not valid. Use: openai | claude | gemini"
        echo "    ('anthropic' and 'google' are NOT accepted -- see .env.production.example)"
        fail=1
        ;;
esac

if [ "$DEBUG" = "True" ]; then
    echo -e "${YELLOW}!${NC} DEBUG=True -- this logs every SQL statement. Set DEBUG=False for production."
fi

if [ "$N8N_PASSWORD" = "change-this-secure-password" ] || [ "$N8N_PASSWORD" = "admin123" ]; then
    echo -e "${YELLOW}!${NC} N8N_PASSWORD is still the default value -- change it."
fi

if [ "$fail" -ne 0 ]; then
    echo ""
    echo -e "${RED}Configuration is incomplete. Fix .env and re-run.${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Configuration validated (LLM provider: ${LLM_PROVIDER:-openai})"
echo -e "${GREEN}✓${NC} Deploying services: ${SERVICES}"

# The n8n service bind-mounts workflow JSON from the sibling directory, which is
# only present in a full-repo checkout.
if [[ "$SERVICES" == *n8n* ]] && [ ! -d ../AIHarvest_Workflow/workflows ]; then
    echo -e "${YELLOW}!${NC} ../AIHarvest_Workflow/workflows not found -- n8n would start with no workflows."
fi

# Stop existing containers
echo ""
echo -e "${YELLOW}Stopping existing containers...${NC}"
$DC down || true

# Build images
echo ""
echo -e "${YELLOW}Building Docker images (this may take several minutes)...${NC}"
$DC build --no-cache $SERVICES

# Start services
echo ""
echo -e "${YELLOW}Starting services...${NC}"
$DC up -d $SERVICES

# Wait for services to be healthy
echo ""
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 10

# Check container status
echo ""
echo "Container Status:"
$DC ps

# Check backend health
echo ""
echo -e "${YELLOW}Checking backend health...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Backend is healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗${NC} Backend health check failed"
        echo "Check logs with: $DC logs backend"
    fi
    echo "Waiting for backend to be ready... ($i/30)"
    sleep 2
done

# Report what the backend thinks its database and provider are
echo ""
echo -e "${YELLOW}Backend health detail:${NC}"
curl -s http://localhost:8000/health || true
echo ""

# Check frontend
echo ""
echo -e "${YELLOW}Checking frontend...${NC}"
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Frontend is accessible"
else
    echo -e "${RED}✗${NC} Frontend is not accessible"
    echo "Check logs with: $DC logs frontend"
fi

# Summary
HOST_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "========================================="
echo ""
echo "Access your application:"
echo "  Frontend:  http://${HOST_IP}:3000"
echo "  Backend:   http://${HOST_IP}:8000"
echo "  API Docs:  http://${HOST_IP}:8000/docs"
if [[ "$SERVICES" == *n8n* ]]; then
    echo "  n8n:       http://${HOST_IP}:5678"
fi
echo ""
echo "Useful commands:"
echo "  View logs:     $DC logs -f"
echo "  Stop services: $DC stop"
echo "  Restart:       $DC restart"
echo ""
echo "For more information, see DEPLOYMENT.md"
echo ""
