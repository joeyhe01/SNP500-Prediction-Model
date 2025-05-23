#!/bin/bash

# Exit on error
set -e

echo "Setting up Flask-React application with News API..."

# Create and activate Python virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install flask requests

# Create directories if they don't exist
echo "Setting up project structure..."
mkdir -p static/js/src/components
mkdir -p static/js/dist
mkdir -p static/css
mkdir -p templates

# Note about React setup
echo ""
echo "React frontend setup instructions (to be run when needed):"
echo "1. Install Node.js dependencies:"
echo "   npm init -y"
echo "   npm install react react-dom"
echo "   npm install --save-dev @babel/core @babel/preset-env @babel/preset-react babel-loader webpack webpack-cli"
echo ""
echo "2. Build the React frontend:"
echo "   npm run build"
echo ""

echo "Setup complete! You can now run the application:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Start the Flask server with a custom port (to avoid AirPlay conflict):"
echo "   python app.py --port=5001"
echo ""
echo "Once running, you can access:"
echo "- News API at: http://127.0.0.1:5001/api/news"
echo "- Frontend at: http://127.0.0.1:5001/ (after React setup)"
echo ""
echo "To test the News API, run the test script:"
echo "   ./test_news_api.py 5001" 