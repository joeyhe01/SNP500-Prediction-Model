#!/bin/bash

# S&P 500 Trading Simulation Dashboard - Stop Script
# This script stops both the React frontend and Flask backend

echo "🛑 Stopping S&P 500 Trading Simulation Dashboard..."
echo ""

# Function to check if a process was killed
check_and_kill() {
    local process_name="$1"
    local kill_command="$2"
    
    if eval "$kill_command" 2>/dev/null; then
        echo "✅ Stopped $process_name"
        return 0
    else
        echo "ℹ️  No $process_name processes were running"
        return 1
    fi
}

# Kill Flask backend processes
echo "🔧 Stopping Flask backend..."
check_and_kill "Flask backend" "pkill -f 'python.*app.py'"

# Kill React frontend processes
echo "🔧 Stopping React frontend..."
check_and_kill "React frontend" "pkill -f 'react-scripts'"

# Kill any npm start processes
echo "🔧 Stopping npm processes..."
check_and_kill "npm start processes" "pkill -f 'npm.*start'"

# Kill any Node.js processes running on port 3000
echo "🔧 Stopping Node.js processes..."
check_and_kill "Node.js processes" "pkill -f 'node.*3000'"

# Kill any concurrently processes
echo "🔧 Stopping concurrently processes..."
check_and_kill "concurrently processes" "pkill -f 'concurrently'"

# Check for any remaining processes on our ports
echo ""
echo "🔍 Checking for remaining processes on ports 3000 and 5001..."

# Check port 3000 (React)
if lsof -ti:3000 >/dev/null 2>&1; then
    echo "⚠️  Port 3000 still in use, force killing..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    echo "✅ Force killed processes on port 3000"
else
    echo "✅ Port 3000 is now free"
fi

# Check port 5001 (Flask)
if lsof -ti:5001 >/dev/null 2>&1; then
    echo "⚠️  Port 5001 still in use, force killing..."
    lsof -ti:5001 | xargs kill -9 2>/dev/null || true
    echo "✅ Force killed processes on port 5001"
else
    echo "✅ Port 5001 is now free"
fi

echo ""
echo "🎉 All dashboard processes have been stopped!"
echo "   You can now run ./start.sh to start fresh"
echo "" 