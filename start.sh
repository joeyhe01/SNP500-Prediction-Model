#!/bin/bash

# Exit on error
set -e

# Default port (can be overridden with -p or --port)
PORT=5001
SKIP_REACT=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -p|--port)
      PORT="$2"
      shift 2
      ;;
    --skip-react)
      SKIP_REACT=true
      shift
      ;;
    -h|--help)
      echo "Usage: ./start.sh [OPTIONS]"
      echo "Options:"
      echo "  -p, --port PORT    Specify the port to run the application (default: 5001)"
      echo "  --skip-react       Skip React setup check (use with API-only usage)"
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

# Check if virtual environment exists
if [ ! -d "venv" ]; then
  echo "Virtual environment not found. Running setup first..."
  if [ "$SKIP_REACT" = true ]; then
    ./setup.sh --skip-react
  else
    ./setup.sh
  fi
else
  echo "Using existing virtual environment."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check for placeholder bundle.js and advise about React setup if needed
if [ "$SKIP_REACT" = false ] && grep -q "Placeholder" static/js/dist/bundle.js 2>/dev/null; then
  echo ""
  echo "=== NOTICE: React frontend not built ==="
  echo "You're running with a placeholder React bundle."
  echo "For the full React experience, run:"
  echo "  npm install"
  echo "  npm run build"
  echo ""
fi

# Start the Flask application
echo "Starting Flask application on port $PORT..."
echo "- Access the application at: http://127.0.0.1:$PORT/"
echo "- Access the news API at: http://127.0.0.1:$PORT/api/news"
echo ""
echo "Press Ctrl+C to stop the server."

python app.py --port=$PORT 