#!/usr/bin/env python3
import requests
import json
import sys

def test_news_api(port=5000):
    """
    Simple script to test the News API endpoint
    """
    try:
        url = f"http://127.0.0.1:{port}/api/news"
        print(f"Testing News API endpoint at: {url}")
        
        # Send a GET request to the endpoint
        response = requests.get(url)
        
        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()
            
            # Pretty print the JSON response
            print(json.dumps(data, indent=2))
            
            # Print a summary
            if data.get('status') == 'ok':
                articles = data.get('articles', [])
                print(f"\nFound {len(articles)} articles")
                
                # Print article titles
                for i, article in enumerate(articles, 1):
                    print(f"{i}. {article.get('title')}")
            else:
                print(f"API Error: {data.get('message', 'Unknown error')}")
        else:
            print(f"HTTP Error: {response.status_code} - {response.reason}")
    
    except requests.exceptions.ConnectionError:
        print(f"Connection Error: Could not connect to http://127.0.0.1:{port}")
        print("Make sure the Flask application is running and accessible.")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    # Get port from command line argument if provided
    port = 5000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("Invalid port number. Using default port 5000.")
    
    test_news_api(port) 