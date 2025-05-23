from flask import Flask, render_template, jsonify
import requests
import argparse

app = Flask(__name__)

# News API key
NEWS_API_KEY = "8ae57769ebca40d68840b4850ddddd54"
NEWS_API_BASE_URL = "https://newsapi.org/v2"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/news', methods=['GET'])
def get_top_headlines():
    """
    Endpoint to fetch top headlines from News API
    """
    try:
        # Build the request URL
        url = f"{NEWS_API_BASE_URL}/top-headlines"
        
        # Default parameters
        params = {
            'apiKey': NEWS_API_KEY,
            'country': 'us',  # Default to US news
            'pageSize': 10    # Limit to 10 articles
        }
        
        # Make the request to News API
        response = requests.get(url, params=params)
        
        # Check if the request was successful
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'status': 'error',
                'message': f"News API error: {response.status_code} - {response.reason}",
                'error': response.json()
            }), response.status_code
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f"An error occurred: {str(e)}"
        }), 500

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run the Flask application')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the application on')
    args = parser.parse_args()
    
    # Run the application on the specified port
    print(f"Starting application on port {args.port}...")
    print(f"- Access the application at: http://127.0.0.1:{args.port}/")
    print(f"- Access the news API at: http://127.0.0.1:{args.port}/api/news")
    app.run(debug=True, port=args.port) 