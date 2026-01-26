#!/bin/bash

# MyCloset - Startup Script

set -e  # Exit on error

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Copy .env.example to .env and add your API key."
    echo "  cp .env.example .env"
    echo ""
fi

# Navigate to backend directory
cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip first
echo "Upgrading pip..."
pip install --upgrade pip -q

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Failed to install dependencies."
    echo "If you're using Python 3.14, some packages may not be compatible yet."
    echo "Try using Python 3.11 or 3.12 instead:"
    echo "  python3.12 -m venv venv"
    exit 1
fi

# Load environment variables
if [ -f "../.env" ]; then
    export $(cat ../.env | grep -v '^#' | xargs)
fi

# Start the server
echo ""
echo "Starting MyCloset server..."
echo "Open http://localhost:8000 in your browser"
echo ""

python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
