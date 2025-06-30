#!/bin/bash
set -e

echo "🔧 Installing backend Python dependencies..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "📁 Installing frontend npm dependencies and building static files..."
cd frontend
npm install
npm run build
cd ..

echo "✅ Setup complete! All dependencies installed and frontend built."