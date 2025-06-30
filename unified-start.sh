#!/bin/bash
set -e

# Activate Python venv
source venv/bin/activate

# Start backend (Flask) and frontend (React) concurrently
echo "🚀 Starting backend and frontend..."

# Start backend
python app.py &

# Start frontend
cd frontend
npm start &

# Wait for both to exit (Ctrl+C to stop)
wait