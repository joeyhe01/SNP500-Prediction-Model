#!/bin/bash

# S&P 500 Trading Simulation Dashboard - Start Script
# This script starts both the React frontend and Flask backend

echo "🚀 Starting S&P 500 Trading Simulation Dashboard..."
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js is not installed. Please install Node.js 16+ and try again."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ Error: npm is not installed. Please install npm and try again."
    exit 1
fi

# Check if Python is installed
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python is not installed. Please install Python and try again."
    exit 1
fi

# Navigate to frontend directory
echo "📁 Navigating to frontend directory..."
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing npm dependencies..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ Error: Failed to install npm dependencies."
        exit 1
    fi
fi

echo "🔧 Starting both React frontend and Flask backend..."
echo ""
echo "Frontend will be available at: http://localhost:3000"
echo "Backend API will be available at: http://localhost:5001"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Start both servers using the npm script
npm start 