# Flask-React News API Application

A Flask application with React frontend integration and News API endpoint.

## Quick Start

The easiest way to get started is to use the setup and start scripts:

```bash
# Set up everything (both Flask and React)
./setup.sh

# To skip React setup (faster, but only API functionality)
./setup.sh --skip-react

# Start the application
./start.sh
```

The start script will:
1. Set up the environment if it doesn't exist
2. Activate the virtual environment
3. Start the Flask application on port 5001

You can specify a different port if needed:
```bash
./start.sh --port 8000
```

## Viewing Options

You have three ways to view the news headlines:

1. **React View** (requires npm and build):
   ```
   http://127.0.0.1:5001/
   ```

2. **Plain HTML View** (no React required):
   ```
   http://127.0.0.1:5001/plain-news
   ```

3. **Raw JSON API** (for developers):
   ```
   http://127.0.0.1:5001/api/news
   ```

The plain HTML view is particularly useful when you don't want to set up React or just need a quick view of the headlines.

## Setup Options

The setup script offers these options:

- Default (no arguments): Sets up both Flask backend and React frontend
- `--skip-react`: Sets up only the Flask backend, skipping React
- `--help`: Shows available options

## Manual Setup

If you prefer to set up manually:

1. Set up the backend:
   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install flask requests
   ```

2. Set up the frontend (optional):
   ```
   npm install
   npm run build
   ```

3. Start the Flask application:
   ```
   source venv/bin/activate
   python app.py --port=5001
   ```

   Note: Port 5001 is suggested to avoid conflicts with AirPlay Receiver on macOS.

## Development Workflow

For React development with hot-reloading:
```
npm run dev
```

This will automatically rebuild the bundle when you make changes to React files.

## Testing the API

You can use the provided test script to test the News API:
```
./test_news_api.py 5001
```

## Project Structure

- `app.py` - The main Flask application file
- `setup.sh` - Script to set up the environment (both Flask and React)
- `start.sh` - Script to start the application
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
