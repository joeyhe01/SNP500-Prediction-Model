import requests
import json
import pandas as pd
import os
import sys
from datetime import datetime

def get_financial_data_newsapi(query="Apple", from_date="2021-01-01", to_date="2021-12-31", api_key=None):
    """
    Fetch financial news data from NewsAPI and save to JSON and CSV files
    
    Args:
        query (str): Search query
        from_date (str): Start date in YYYY-MM-DD format
        to_date (str): End date in YYYY-MM-DD format
        api_key (str): NewsAPI API key
    """
    if api_key is None or api_key == "YOUR_API_KEY":
        api_key = os.environ.get('NEWSAPI_KEY')
        if api_key is None:
            print("ERROR: API key not provided.")
            print("You need to either:")
            print("1. Set the NEWSAPI_KEY environment variable, or")
            print("2. Provide the API key as a command line argument, or")
            print("3. Edit the script to add your API key")
            print("\nUsage: python newsapi_fetcher.py [API_KEY] [QUERY] [FROM_DATE] [TO_DATE]")
            print("Example: python newsapi_fetcher.py 1a2b3c4d5e6f7g8h9i0j Apple 2021-01-01 2021-12-31")
            sys.exit(1)
    
    print(f"Fetching news data for query: '{query}' from {from_date} to {to_date}")
    
    # Construct the API URL
    base_url = "https://newsapi.org/v2/everything"
    params = {
        'q': query,
        'from': from_date,
        'to': to_date,
        'apiKey': api_key,
        'pageSize': 100  # Maximum allowed by the API
    }
    
    all_articles = []
    page = 1
    total_results = None
    
    # Get all pages of results
    while total_results is None or len(all_articles) < total_results:
        params['page'] = page
        response = requests.get(base_url, params=params)
        
        if response.status_code != 200:
            print(f"Error fetching data: {response.status_code}")
            print(response.json())
            break
        
        data = response.json()
        
        if total_results is None:
            total_results = data.get('totalResults', 0)
            print(f"Total articles found: {total_results}")
        
        articles = data.get('articles', [])
        if not articles:
            break
            
        all_articles.extend(articles)
        print(f"Fetched page {page}, got {len(articles)} articles. Total: {len(all_articles)}/{total_results}")
        
        page += 1
    
    # Create timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"news_{query}_{from_date}_{to_date}_{timestamp}.json"
    csv_filename = f"news_{query}_{from_date}_{to_date}_{timestamp}.csv"
    
    # Save to JSON
    with open(json_filename, 'w') as f:
        json.dump({"articles": all_articles}, f, indent=2)
    
    # Convert to DataFrame and save to CSV
    if all_articles:
        df = pd.json_normalize(all_articles)
        df.to_csv(csv_filename, index=False)
        
        print(f"Saved {len(all_articles)} articles to {json_filename} and {csv_filename}")
    else:
        print("No articles found to save")

if __name__ == "__main__":
    # Parse command line arguments
    api_key = "YOUR_API_KEY"
    query = "Apple"
    from_date = "2021-01-01"
    to_date = "2021-12-31"
    
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
    if len(sys.argv) > 2:
        query = sys.argv[2]
    if len(sys.argv) > 3:
        from_date = sys.argv[3]
    if len(sys.argv) > 4:
        to_date = sys.argv[4]
    
    get_financial_data_newsapi(query=query, from_date=from_date, to_date=to_date, api_key=api_key) 