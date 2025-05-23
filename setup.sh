#!/bin/bash

# Exit on error
set -e

# Default settings
SKIP_REACT=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-react)
      SKIP_REACT=true
      shift
      ;;
    -h|--help)
      echo "Usage: ./setup.sh [OPTIONS]"
      echo "Options:"
      echo "  --skip-react       Skip React/npm installation"
      echo "  -h, --help         Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help to see available options"
      exit 1
      ;;
  esac
done

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

# Set up React frontend
if [ "$SKIP_REACT" = false ]; then
  echo ""
  echo "===== SETTING UP REACT FRONTEND ====="
  
  if command -v npm &> /dev/null; then
    echo "Installing Node.js dependencies..."
    npm install
    
    echo "Building React frontend..."
    npm run build
  else
    echo "Node.js/npm not found. Skipping React setup."
    echo "Please install Node.js and npm, then run 'npm install' and 'npm run build'."
    
    # Create placeholder bundle.js if it doesn't exist
    if [ ! -f static/js/dist/bundle.js ]; then
      echo "Creating placeholder bundle.js..."
      echo "// Placeholder bundle.js
// Run 'npm install' and 'npm run build' to generate the actual bundle
console.log('React not yet built. Please run npm install and npm run build to set up the React frontend.');" > static/js/dist/bundle.js
    fi
  fi
else
  echo ""
  echo "Skipping React setup (--skip-react flag used)"
  
  # Create placeholder bundle.js if it doesn't exist
  if [ ! -f static/js/dist/bundle.js ]; then
    echo "Creating placeholder bundle.js..."
    echo "// Placeholder bundle.js
// Run 'npm install' and 'npm run build' to generate the actual bundle
console.log('React not yet built. Please run npm install and npm run build to set up the React frontend.');" > static/js/dist/bundle.js
  fi
fi

echo ""
echo "===== SETUP COMPLETE ====="
echo ""
echo "The Flask application with News API is now set up."
if [ "$SKIP_REACT" = true ]; then
  echo "Note: React frontend setup was skipped. Run 'npm install' and 'npm run build' to set it up later."
fi
echo ""
echo "To run the application:"
echo "  ./start.sh"
echo ""
echo "Or manually:"
echo "  source venv/bin/activate"
echo "  python app.py --port=5001"
echo ""
echo "To access the application:"
echo "- News API: http://127.0.0.1:5001/api/news"
echo "- Frontend: http://127.0.0.1:5001/" 