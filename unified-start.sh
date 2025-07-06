#!/bin/bash
set -e

# Activate Python venv
#source venv/bin/activate
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
  source venv/Scripts/activate
else
  source venv/bin/activate
fi

# Start backend (Flask) and frontend (React) concurrently
echo "🚀 Starting backend and frontend..."

# Start backend
python app.py &

# Start frontend
cd frontend
npm run start:frontend &

# Wait for both to exit (Ctrl+C to stop)
wait