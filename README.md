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
