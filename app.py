from flask import Flask, render_template, jsonify, send_from_directory, request
import requests
import argparse
import os
import json
from datetime import datetime

app = Flask(__name__)

# News API key
NEWS_API_KEY = "8ae57769ebca40d68840b4850ddddd54"
NEWS_API_BASE_URL = "https://newsapi.org/v2"

@app.route('/')
def index():
    # Check if the user wants the plain HTML view
    if request.args.get('plain') == 'true':
        return plain_news()
    return render_template('index.html')

@app.route('/plain-news')
def plain_news():
    """Simple HTML view of news headlines without requiring React"""
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
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get('articles', [])
            
            # Format the date for each article
            for article in articles:
                if 'publishedAt' in article:
                    try:
                        dt = datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00'))
                        article['formatted_date'] = dt.strftime('%B %d, %Y')
                    except:
                        article['formatted_date'] = article['publishedAt']
            
            # Return a basic HTML page with the news
            return f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Top Headlines</title>
                <style>
                    body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
                    h1 {{ color: #333; }}
                    .article {{ margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid #eee; }}
                    .article img {{ max-width: 100%; height: auto; border-radius: 4px; margin-bottom: 15px; }}
                    .article h2 {{ margin-top: 0; margin-bottom: 5px; }}
                    .article h2 a {{ color: #0066cc; text-decoration: none; }}
                    .article h2 a:hover {{ text-decoration: underline; }}
                    .source {{ color: #666; font-size: 0.9em; margin-top: 0; margin-bottom: 8px; }}
                    .description {{ margin-bottom: 10px; }}
                    .date {{ color: #888; font-size: 0.8em; }}
                    .toggle-view {{ margin-bottom: 20px; }}
                    .toggle-view a {{ color: #0066cc; text-decoration: none; padding: 5px 10px; 
                                   border: 1px solid #0066cc; border-radius: 4px; }}
                </style>
            </head>
            <body>
                <div class="toggle-view">
                    <a href="/">Switch to React View</a>
                    <a href="/api/news">View Raw JSON</a>
                </div>
                <h1>Top Headlines</h1>
                {''.join([f"""
                <div class="article">
                    {f'<img src="{article["urlToImage"]}" alt="{article["title"]}">' if article.get('urlToImage') else ''}
                    <h2><a href="{article['url']}" target="_blank">{article['title']}</a></h2>
                    <p class="source">{article['source']['name']}</p>
                    <p class="description">{article.get('description', '')}</p>
                    <p class="date">{article.get('formatted_date', '')}</p>
                </div>
                """ for article in articles])}
            </body>
            </html>
            """
        else:
            return f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Error</title>
                <style>
                    body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                    .error {{ background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 4px; }}
                </style>
            </head>
            <body>
                <div class="error">
                    <h1>Error Loading News</h1>
                    <p>News API error: {response.status_code} - {response.reason}</p>
                    <p>{json.dumps(response.json())}</p>
                </div>
            </body>
            </html>
            """
    except Exception as e:
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                .error {{ background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <div class="error">
                <h1>Error Loading News</h1>
                <p>An error occurred: {str(e)}</p>
            </div>
        </body>
        </html>
        """

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

# Custom static files handler to provide better error messages
@app.route('/static/<path:filename>')
def custom_static(filename):
    file_path = os.path.join(app.root_path, 'static', filename)
    if not os.path.exists(file_path):
        app.logger.warning(f"Static file not found: {filename}")
        # For JS files that might be missing due to no build
        if filename.endswith('.js') and 'bundle' in filename:
            return """
            // React bundle not found. 
            // Please run 'npm install' and 'npm run build' to generate the bundle.
            console.error('React bundle not found. Please run npm install and npm run build.');
            """, 200, {'Content-Type': 'application/javascript'}
    return send_from_directory('static', filename)

# Handle 404 errors
@app.errorhandler(404)
def page_not_found(e):
    return jsonify({
        'status': 'error',
        'message': 'The requested resource was not found'
    }), 404

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run the Flask application')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the application on')
    args = parser.parse_args()
    
    # Run the application on the specified port
    print(f"Starting application on port {args.port}...")
    print(f"- Access the application at: http://127.0.0.1:{args.port}/")
    print(f"- Access plain HTML view at: http://127.0.0.1:{args.port}/plain-news")
    print(f"- Access the news API at: http://127.0.0.1:{args.port}/api/news")
    print("\nNote: To set up the React frontend:")
    print("1. Run 'npm install' to install dependencies")
    print("2. Run 'npm run build' to build the frontend")
    app.run(debug=True, port=args.port) 