import finnhub
import datetime
import time
import json
import os

# Initialize Finnhub client with API key
finnhub_client = finnhub.Client(api_key="d0p1oc1r01qr8ds0v5j0d0p1oc1r01qr8ds0v5jg")

def fetch_daily_news_for_2022():
    """
    Fetches market news for every day in 2022 and saves it to a single JSON file.
    Retries on rate limit until successful.
    """
    # Create directory for saving data if it doesn't exist
    output_dir = 'data/news'
    os.makedirs(output_dir, exist_ok=True)
    
    # Define the date range for 2022
    start_date = datetime.date(2022, 1, 1)
    end_date = datetime.date(2022, 12, 31)
    current_date = start_date
    
    # Initialize dictionary to store all news data
    all_news_data = {}
    
    # Load existing data if available
    output_file = f"{output_dir}/all_news_2022.json"
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                all_news_data = json.load(f)
            print(f"Loaded existing data with {len(all_news_data)} days")
        except Exception as e:
            print(f"Error loading existing data: {e}")
    
    while current_date <= end_date:
        # Format date string
        date_str = current_date.strftime("%Y-%m-%d")
        
        # Skip if we already have data for this date
        if date_str in all_news_data:
            print(f"Skipping {date_str}, already have data")
            current_date += datetime.timedelta(days=1)
            continue
        
        # Keep trying until we get the data
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Get news for the current date
                # According to the documentation, we need to use 'category' parameter
                # and min_id parameter for general news
                news = finnhub_client.general_news('general', min_id=0)
                
                # Process news items to convert datetime to string
                processed_news = []
                for item in news:
                    # Make a copy of the item to modify
                    processed_item = item.copy()
                    
                    # Convert datetime fields to string if they exist
                    if 'datetime' in processed_item:
                        # Convert UNIX timestamp to readable date string
                        timestamp = processed_item['datetime']
                        date_obj = datetime.datetime.fromtimestamp(timestamp)
                        processed_item['datetime_str'] = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                    
                    processed_news.append(processed_item)
                
                # Add the processed news data to our dictionary with date as key
                all_news_data[date_str] = processed_news
                
                print(f"Fetched news for {date_str}")
                
                # Sleep to avoid hitting API rate limits (60 calls per minute)
                time.sleep(0.5)
                
                # Break out of the retry loop when successful
                break
                
            except Exception as e:
                error_message = str(e).lower()
                print(f"Error fetching news for {date_str}: {e}")
                
                # Check for rate limit in the error message
                if "429" in error_message or "limit" in error_message or "api limit reached" in error_message:
                    retry_count += 1
                    retry_wait = 65  # Wait a bit longer than 60 seconds to be safe
                    print(f"Rate limit hit, waiting {retry_wait} seconds before retry {retry_count}/{max_retries}...")
                    
                    # Save our progress before waiting
                    with open(output_file, 'w') as f:
                        json.dump(all_news_data, f, indent=4)
                    print(f"Saved progress while waiting for rate limit reset")
                    
                    time.sleep(retry_wait)
                else:
                    # For other errors, just skip this date
                    print(f"Skipping date {date_str} due to non-rate-limit error")
                    break
            
            # If we've exhausted all retries, move on
            if retry_count >= max_retries:
                print(f"Exhausted all retries for {date_str}, moving on")
                break
            
        # Move to the next day
        current_date += datetime.timedelta(days=1)
        
        # Periodically save the data we've collected so far
        if current_date.day == 1 or current_date > end_date:  # Save at the beginning of each month
            print(f"Saving progress up to {date_str}...")
            with open(output_file, 'w') as f:
                json.dump(all_news_data, f, indent=4)
    
    # Save all news data to a single JSON file at the end
    with open(output_file, 'w') as f:
        json.dump(all_news_data, f, indent=4)
    
    print(f"Finished fetching news for all days in 2022 and saved to {output_file}")
    print(f"Successfully fetched data for {len(all_news_data)} days")

if __name__ == "__main__":
    fetch_daily_news_for_2022()