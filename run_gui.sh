#!/bin/bash

# FreEco.AI GUI Server Startup Script

echo "🌿 FreEco.AI GUI Server"
echo "======================"
echo ""

# Check if running from correct directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: Please run this script from the FreEco.AI root directory"
    exit 1
fi

# Check Python version
python3 --version

# Install dependencies if needed
echo ""
echo "📦 Checking dependencies..."
pip3 install -q fastapi uvicorn pydantic aiohttp

# Start the GUI server
echo ""
echo "🚀 Starting GUI server on http://localhost:8000"
echo "📖 API docs available at http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 -m uvicorn app.gui_server:app --host 0.0.0.0 --port 8000 --reload
