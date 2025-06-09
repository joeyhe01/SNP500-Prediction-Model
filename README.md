# S&P 500 Prediction Model

A comprehensive trading simulation system that uses news sentiment analysis to predict S&P 500 movements with a modern React dashboard for performance analysis.

## 🚀 Quick Start

### Option 1: One-Command Start (Recommended)
```bash
# From the project root directory
./start.sh
```

### Option 2: Frontend Directory Start
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (first time only)
npm install

# Start both frontend and backend
npm start
```

### Stop the Application
```bash
# Stop both frontend and backend
./stop.sh
```

Both options will:
- Start the Flask backend API on port 5001
- Start the React frontend on port 3000
- Open your browser to http://localhost:3000
- Display logs from both servers

## 📊 Dashboard Features

- **Interactive Charts**: View cumulative returns across multiple simulations
- **Drill-Down Analysis**: Click simulations → days → individual news articles
- **Trading Details**: See exact buy/sell orders and their performance
- **Sentiment Analysis**: View how news sentiment influenced trading decisions
- **Responsive Design**: Works on desktop and mobile devices

---

## Project Overview

# Flask-React News API Application

A Flask application with React frontend integration and News API endpoint.

## Setup

1. Run the setup script to create a virtual environment and install dependencies:
   ```
   ./setup.sh
   ```

2. Start the Flask application:
   ```
   source venv/bin/activate
   python app.py --port=5001
   ```

   Note: Port 5001 is suggested to avoid conflicts with AirPlay Receiver on macOS.

3. Access the API endpoint at:
   ```
   http://127.0.0.1:5001/api/news
   ```

## React Frontend Setup (Optional)

Follow these steps when you want to set up the React frontend:

1. Install Node.js dependencies:
   ```
   npm install
   ```

2. Build the React frontend:
   ```
   npm run build
   ```

   For development with hot-reloading:
   ```
   npm run dev
   ```

3. After building, you can access the React frontend at:
   ```
   http://127.0.0.1:5001/
   ```

## Testing the API

You can use the provided test script to test the News API:
```
./test_news_api.py 5001
```

## Project Structure

- `app.py` - The main Flask application file
- `templates/` - HTML templates
- `static/` - Static files
  - `css/` - CSS files
  - `js/src/` - React source files
  - `js/dist/` - Compiled JavaScript files
- `package.json` - Node.js dependencies
- `webpack.config.js` - Webpack configuration

## API Endpoints

- `/api/news` - Returns top headlines from News API
  - Currently fetches top 10 headlines from the US

## Configuration

The application uses the following configuration:
- News API Key: 8ae57769ebca40d68840b4850ddddd54
- Default country: US
- Default page size: 10 articles
