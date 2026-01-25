#!/bin/bash

# MyCloset - Startup Script

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

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -q

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
