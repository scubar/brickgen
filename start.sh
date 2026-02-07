#!/bin/bash
# Quick start script for BrickGen

set -e

echo "BrickGen - Quick Start Script"
echo "=============================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your API keys!"
    echo ""
    echo "Get API keys from:"
    echo "  - Brickset: https://brickset.com/tools/webservices/requestkey"
    echo "  - Rebrickable: https://rebrickable.com/api/"
    echo ""
    read -p "Press Enter after you've added your API keys to .env..."
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "Building and starting BrickGen..."
docker-compose up -d --build

echo ""
echo "✅ BrickGen is starting up!"
echo ""
echo "The application will be available at: http://localhost:8000"
echo ""
echo "On first run, the LDraw library will be downloaded (~100MB)."
echo "This may take a few minutes."
echo ""
echo "Monitor logs with: docker-compose logs -f brickgen"
echo "Stop with: docker-compose down"
echo ""
