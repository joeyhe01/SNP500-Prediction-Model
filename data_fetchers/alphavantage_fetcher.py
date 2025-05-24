alpha_vantage_api_key = 'KWL2J50Q32KS3YSM'

import requests
import json
import time
import os
from datetime import datetime, timedelta

def fetch_news_for_date(date, api_key, max_retries=5, retry_delay=5):
    """
    Fetch news articles for a specific date
    
    Args:
        date: Date object to fetch news for
        api_key: Alpha Vantage API key
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
    
    Returns:
        List of simplified news items
    """
    # Format start date (current day at 00:00)
    time_from = date.strftime("%Y%m%dT0000")
    
    # Format end date (next day at 00:00)
    
    print(f"Fetching news from {time_from} ...")
    
    # Construct URL with proper parameters for NEWS_SENTIMENT endpoint
    url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&time_from={time_from}&sort=EARLIEST&apikey={api_key}'
    
    retry_count = 0
    while retry_count <= max_retries:
        try:
            r = requests.get(url)
            data = r.json()
            
            if 'feed' not in data:
                error_msg = data.get('Note', data.get('Information', 'Unknown error'))
                print(f"Warning: No 'feed' in response. Response: {error_msg}")
                
                # If it's a rate limit error, retry
                if 'Thank you for using Alpha Vantage!' in str(error_msg) or 'API call frequency' in str(error_msg):
                    retry_count += 1
                    wait_time = retry_delay * retry_count
                    print(f"  API limit reached. Retry attempt {retry_count}/{max_retries} after {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    # If it's not a rate limit error but a "No articles" response, return empty list
                    return []
            
            # Extract the required fields from each news item
            simplified_news = []
            for item in data['feed']:
                # Get the time published and convert to datetime for filtering
                time_published = item.get('time_published', '')
                if time_published:
                    news_item = {
                        'title': item.get('title', ''),
                        'summary': item.get('summary', ''),
                        'source': item.get('source', ''),
                        'time_published': time_published,
                        'date': time_published[:8]  # Add date field (YYYYMMDD) for easier filtering later
                    }
                    simplified_news.append(news_item)
            
            print(f"  Found {len(simplified_news)} articles for {date.strftime('%Y-%m-%d')}")
            return simplified_news
        
        except Exception as e:
            print(f"Error fetching data: {e}")
            retry_count += 1
            wait_time = retry_delay * retry_count
            
            if retry_count <= max_retries:
                print(f"  Retry attempt {retry_count}/{max_retries} after {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"  Max retries reached. Moving on...")
                return []

    return []  # Return empty list if all retries fail

def process_single_day(date, api_key, output_file):
    """
    Process a single day
    
    Args:
        date: Date to process (datetime object)
        api_key: Alpha Vantage API key
        output_file: Path to output JSON file
    
    Returns:
        Number of articles fetched
    """
    # Fetch news for this date
    news_items = fetch_news_for_date(date, api_key)
    
    # Load existing data if file exists
    existing_news = []
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                existing_news = json.load(f)
            print(f"Loaded {len(existing_news)} existing articles from {output_file}")
        except Exception as e:
            print(f"Error loading existing data: {e}")
    
    # Combine existing and new data
    all_news = existing_news + news_items
    
    # Save all news items to the JSON file
    os.makedirs(os.path.dirname(output_file), exist_ok=True)  # Create directory if it doesn't exist
    with open(output_file, 'w') as f:
        json.dump(all_news, f, indent=2)
    
    print(f"Saved {len(all_news)} total articles to {output_file} ({len(news_items)} new articles for {date.strftime('%Y-%m-%d')})")
    
    # Sleep to respect API rate limits
    time.sleep(1)  # Wait 1 second between API calls
    
    return len(news_items)

def main():
    # Set a fixed output filename
    output_filename = "data/alpha_vantage_news_2023.json"
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    
    # Create empty file if it doesn't exist
    if not os.path.exists(output_filename):
        with open(output_filename, 'w') as f:
            json.dump([], f)
    
    # Set start date and end date
    start_date = datetime(2023, 3, 1)
    end_date = datetime(2024, 3, 1)
    
    # Process each day individually
    current_date = start_date
    total_articles = 0
    
    while current_date <= end_date:
        print(f"\nProcessing date: {current_date.strftime('%Y-%m-%d')}")
        num_articles = process_single_day(current_date, alpha_vantage_api_key, output_filename)
        total_articles += num_articles
        
        # Move to next day
        current_date += timedelta(days=1)
        
        print(f"Total articles collected so far: {total_articles}")
    
    print("\n===================================================================")
    print(f"Process complete: Processed all days from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Total articles collected: {total_articles}")
    print(f"All data saved to: {output_filename}")
    print("===================================================================\n")

if __name__ == "__main__":
    main()
