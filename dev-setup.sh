#!/bin/bash
# Development setup script for BrickGen

set -e

echo "BrickGen - Development Setup"
echo "============================"
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python version: $PYTHON_VERSION"

# Check if pipenv is installed
if ! command -v pipenv &> /dev/null; then
    echo "pipenv not found. Installing pipenv..."
    pip3 install --user pipenv
    echo ""
    echo "⚠️  You may need to add pipenv to your PATH:"
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi

# Setup backend
echo ""
echo "Setting up backend..."
cd backend

echo "Installing Python dependencies with pipenv..."
pipenv install --dev

cd ..

# Setup frontend
echo ""
echo "Setting up frontend..."
cd frontend

if ! command -v npm &> /dev/null; then
    echo "❌ Error: npm is not installed"
    exit 1
fi

echo "Installing Node dependencies..."
npm install

cd ..

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file..."
    cp .env.example .env
    echo "⚠️  Remember to add your API keys to .env!"
fi

echo ""
echo "✅ Development setup complete!"
echo ""
echo "To run the backend:"
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  uvicorn backend.main:app --reload"
echo ""
echo "To run the frontend (in another terminal):"
echo "  cd frontend"
echo "  npm run dev"
echo ""
