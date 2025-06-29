#!/bin/bash

# Golf Pickem League Setup Script
echo "🏌️  Setting up Golf Pickem League..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Make run script executable
chmod +x run_dev.py

# Create data directory if it doesn't exist
mkdir -p data

echo "✅ Setup complete!"
echo ""
echo "🚀 To start the development server:"
echo "   python main.py"
echo ""
echo "   Or using the wrapper script:"
echo "   ./run_dev.py"
echo ""
echo "📍 The application will be available at: http://localhost:5001"
