#!/bin/bash

# Dyson PM System - Production Deployment Script
# This script deploys the application to a test/production server

set -e  # Exit on error

echo "========================================="
echo "Dyson PM System - Deployment Script"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please copy .env.production.example to .env and configure it first:"
    echo "  cp .env.production.example .env"
    echo "  nano .env"
    exit 1
fi

# Source environment variables
source .env

echo -e "${GREEN}✓${NC} Environment file loaded"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed!${NC}"
    echo "Please install Docker first. See DEPLOYMENT.md for instructions."
    exit 1
fi

echo -e "${GREEN}✓${NC} Docker is installed"

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed!${NC}"
    echo "Please install Docker Compose first. See DEPLOYMENT.md for instructions."
    exit 1
fi

echo -e "${GREEN}✓${NC} Docker Compose is installed"

# Stop existing containers
echo ""
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker-compose -f docker-compose.prod.yml down || true

# Build images
echo ""
echo -e "${YELLOW}Building Docker images (this may take several minutes)...${NC}"
docker-compose -f docker-compose.prod.yml build --no-cache

# Start services
echo ""
echo -e "${YELLOW}Starting services...${NC}"
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
echo ""
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 10

# Check container status
echo ""
echo "Container Status:"
docker-compose -f docker-compose.prod.yml ps

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
        echo "Check logs with: docker-compose -f docker-compose.prod.yml logs backend"
    fi
    echo "Waiting for backend to be ready... ($i/30)"
    sleep 2
done

# Check frontend
echo ""
echo -e "${YELLOW}Checking frontend...${NC}"
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Frontend is accessible"
else
    echo -e "${RED}✗${NC} Frontend is not accessible"
    echo "Check logs with: docker-compose -f docker-compose.prod.yml logs frontend"
fi

# Summary
echo ""
echo "========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "========================================="
echo ""
echo "Access your application:"
echo "  Frontend:  http://$(hostname -I | awk '{print $1}'):3000"
echo "  Backend:   http://$(hostname -I | awk '{print $1}'):8000"
echo "  API Docs:  http://$(hostname -I | awk '{print $1}'):8000/docs"
echo "  n8n:       http://$(hostname -I | awk '{print $1}'):5678"
echo ""
echo "Useful commands:"
echo "  View logs:     docker-compose -f docker-compose.prod.yml logs -f"
echo "  Stop services: docker-compose -f docker-compose.prod.yml stop"
echo "  Restart:       docker-compose -f docker-compose.prod.yml restart"
echo ""
echo "For more information, see DEPLOYMENT.md"
echo ""
