alpha_vantage_api_key = 'KWL2J50Q32KS3YSM'

import requests
import json
import time
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path to allow imports when running directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import get_db_session, News
from sqlalchemy.exc import IntegrityError

def fetch_news_for_topic(topic, time_from, api_key, max_retries=5, retry_delay=5):
    """
    Fetch news articles for a specific topic
    
    Args:
        topic: Topic to fetch news for (earnings, financial_markets, finance, technology)
        time_from: Start time in YYYYMMDDTHHMM format
        api_key: Alpha Vantage API key
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
    
    Returns:
        List of news items
    """
    print(f"Fetching {topic} news from {time_from} ...")
    
    # Construct URL with topic parameter
    url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&topics={topic}&time_from={time_from}&limit=50&sort=EARLIEST&apikey={api_key}'
    
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
                    return []
            
            print(f"  Found {len(data.get('feed', []))} {topic} articles")
            return data.get('feed', [])
        
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

    return []

def save_news_to_db(news_items, session):
    """
    Save news items to database
    
    Args:
        news_items: List of news items to save
        session: Database session
    
    Returns:
        Number of successfully saved items
    """
    saved_count = 0
    
    for item in news_items:
        try:
            # Parse time_published
            time_str = item.get('time_published', '')
            if time_str:
                # Format: YYYYMMDDTHHMMSS
                time_published = datetime.strptime(time_str, '%Y%m%dT%H%M%S')
                
                news = News(
                    title=item.get('title', ''),
                    summary=item.get('summary', ''),
                    source=item.get('source', ''),
                    url=item.get('url', ''),
                    time_published=time_published
                )
                
                session.add(news)
                session.commit()
                saved_count += 1
                
        except IntegrityError:
            # URL already exists, skip
            session.rollback()
            continue
        except Exception as e:
            print(f"Error saving news item: {e}")
            session.rollback()
            continue
    
    return saved_count

def fetch_news_for_date_range(start_date, end_date, api_key):
    """
    Fetch news for a date range from multiple topics
    
    Args:
        start_date: Start date (datetime object)
        end_date: End date (datetime object)
        api_key: Alpha Vantage API key
    
    Returns:
        Total number of articles saved
    """
    session = get_db_session()
    topics = ['earnings', 'financial_markets', 'finance', 'technology']
    total_saved = 0
    
    current_date = start_date
    while current_date <= end_date:
        # Format time_from for API (YYYYMMDDTHHMM)
        time_from = current_date.strftime("%Y%m%dT0000")
        
        print(f"\nProcessing date: {current_date.strftime('%Y-%m-%d')}")
        
        for topic in topics:
            # Fetch news for this topic
            news_items = fetch_news_for_topic(topic, time_from, api_key)
            
            # Save to database
            if news_items:
                saved_count = save_news_to_db(news_items, session)
                total_saved += saved_count
                print(f"  Saved {saved_count} {topic} articles to database")
            
            # Rate limit: wait between API calls
            time.sleep(1)
        
        # Move to next day
        current_date += timedelta(days=1)
    
    session.close()
    return total_saved

def main():
    """
    Main function to fetch news for the simulation period
    """
    # Set date range
    start_date = datetime(2022, 3, 1)
    end_date = datetime(2024, 3, 1)
    
    print(f"Fetching news from {start_date} to {end_date}")
    print("Topics: earnings, financial_markets, finance, technology")
    print("=" * 60)
    
    # Initialize database
    from models.database import init_database
    init_database()
    
    # Fetch and save news
    total_saved = fetch_news_for_date_range(start_date, end_date, alpha_vantage_api_key)
    
    print("\n" + "=" * 60)
    print(f"Process complete!")
    print(f"Total articles saved to database: {total_saved}")
    print("=" * 60)

if __name__ == "__main__":
    main()
