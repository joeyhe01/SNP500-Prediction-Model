#!/usr/bin/env python3
"""
Backfill simulation data script
Fetches news articles and stock price data for June 2025 from EODHD API
and stores them in the database for simulation purposes.
"""

import requests
import time
import json
from datetime import datetime, date, timedelta
from sqlalchemy.exc import IntegrityError
from models.database import get_db_session, News, StockPrice

# API Configuration
API_KEY = "6888359d906c44.03885468"
BASE_URL = "https://eodhd.com/api"

# S&P 500 tickers list (from llm_sentiment_model.py)
SP500_TICKERS = {
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'JPM', 'JNJ', 'V',
    'PG', 'UNH', 'HD', 'MA', 'DIS', 'BAC', 'NFLX', 'ADBE', 'CRM', 'PFE',
    'CSCO', 'INTC', 'WMT', 'IBM', 'BA', 'GS', 'MS', 'CVX', 'XOM', 'VZ',
    'T', 'KO', 'PEP', 'NKE', 'MRK', 'ABBV', 'TMO', 'COST', 'AVGO', 'ORCL',
    'ACN', 'LLY', 'TXN', 'MCD', 'QCOM', 'DHR', 'NEE', 'BMY', 'UPS', 'RTX',
    'LOW', 'SPGI', 'INTU', 'AMD', 'CAT', 'MDLZ', 'GE', 'MMM', 'CVS', 'AMT',
    'AXP', 'DE', 'BKNG', 'AMAT', 'TJX', 'ISRG', 'ADP', 'GILD', 'CME', 'TMUS',
    'REGN', 'C', 'VRTX', 'BLK', 'ZTS', 'NOW', 'PANW', 'SYK', 'BSX', 'SNOW',
    'UBER', 'SBUX', 'SPOT', 'ABNB', 'PYPL', 'SQ', 'COIN', 'ROKU', 'ZM', 'DOCU',
    'ETSY', 'SHOP', 'TWLO', 'SNAP', 'PINS', 'LYFT', 'DBX', 'W', 'PTON', 'HOOD',
    'F', 'GM', 'RIVN', 'LCID', 'NIO', 'LI', 'XPEV', 'PLTR', 'NET', 'DDOG',
    'CRWD', 'OKTA', 'MDB', 'TEAM', 'FTNT', 'WDAY', 'ADSK', 'EA', 'TTWO', 'ATVI',
    'RBLX', 'U', 'MSCI', 'MCO', 'ICE', 'NDAQ', 'CBOE', 'WFC', 'USB', 'PNC',
    'TFC', 'SCHW', 'COF', 'AIG', 'MET', 'PRU', 'TRV', 'AFL', 'ALL', 'PGR',
    'CB', 'HIG', 'WBA', 'CI', 'HUM', 'CNC', 'ELV'
}

def fetch_news_for_ticker(ticker, from_date, to_date, limit=50, offset=0):
    """
    Fetch news articles for a specific ticker and date range using the correct EODHD API format
    """
    url = f'https://eodhd.com/api/news'
    params = {
        's': f'{ticker}.US',
        'from': from_date,
        'to': to_date,
        'offset': offset,
        'limit': limit,
        'api_token': API_KEY,
        'fmt': 'json'
    }
    
    try:
        print(f"Fetching news for {ticker} from {from_date} to {to_date} (offset={offset}, limit={limit})...")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        # Add delay to respect API rate limits
        time.sleep(0.2)  # 200ms between requests
        
        data = response.json()
        return data if isinstance(data, list) else []
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching news for {ticker}: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response for {ticker}: {e}")
        return []

def fetch_stock_prices(ticker, from_date, to_date):
    """
    Fetch historical stock price data for a ticker within a date range
    """
    url = f"{BASE_URL}/eod/{ticker}.US"
    params = {
        'from': from_date,
        'to': to_date,
        'api_token': API_KEY,
        'fmt': 'json'
    }
    
    try:
        print(f"Fetching stock prices for {ticker} from {from_date} to {to_date}...")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        # Add delay to respect API rate limits
        time.sleep(0.1)  # 100ms between requests
        
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching stock prices for {ticker}: {e}")
        return []

def parse_article_date(date_str, target_date):
    """
    Parse article date from various formats that EODHD API might return
    """
    if not date_str:
        return datetime.combine(target_date, datetime.min.time())
    
    # Try different date formats
    date_formats = [
        '%Y-%m-%dT%H:%M:%S+00:00',  # 2025-08-01T16:24:00+00:00
        '%Y-%m-%dT%H:%M:%S%z',     # with timezone
        '%Y-%m-%dT%H:%M:%S',       # 2025-08-01T16:24:00
        '%Y-%m-%d %H:%M:%S',       # 2025-08-01 16:24:00
        '%Y-%m-%d',                # 2023-01-03
    ]
    
    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            # Remove timezone info if present to store as naive datetime
            if parsed_date.tzinfo:
                parsed_date = parsed_date.replace(tzinfo=None)
            return parsed_date
        except ValueError:
            continue
    
    # If none of the formats work, use target date
    print(f"Could not parse date '{date_str}', using target date")
    return datetime.combine(target_date, datetime.min.time())

def save_news_to_db(session, news_data, target_date):
    """
    Save news articles to the database
    """
    saved_count = 0
    
    for article in news_data:
        try:
            # Parse the published date from the article
            date_str = article.get('date', '')
            published_date = parse_article_date(date_str, target_date)
            
            # Debug: Print the first article structure to understand the API response
            if saved_count == 0:
                print(f"DEBUG: First article fields: {list(article.keys())}")
                print(f"DEBUG: Sample article: {article}")
            
            # Create News object - handle different possible field names from EODHD API
            title = article.get('title') or article.get('headline', 'No Title')
            content = article.get('content') or article.get('summary') or article.get('description', '')
            source = article.get('source') or article.get('publisher', 'EODHD')
            url = article.get('url') or article.get('link') or f"https://example.com/news/{int(time.time())}-{saved_count}"
            
            news_item = News(
                title=title[:500],  # Limit title length
                summary=content[:1000] if content else None,  # Use content as summary
                source=source,
                url=url,
                time_published=published_date
            )
            
            session.add(news_item)
            session.commit()
            saved_count += 1
            
        except IntegrityError as e:
            # URL already exists, skip this article
            session.rollback()
            print(f"Duplicate article (URL exists): {url}")
            continue
        except Exception as e:
            print(f"Error saving news article: {e}")
            print(f"Article data: {article}")
            session.rollback()
            continue
    
    return saved_count

def save_stock_prices_to_db(session, ticker, price_data):
    """
    Save stock price data to the database
    """
    saved_count = 0
    
    for day_data in price_data:
        try:
            # Parse the date
            price_date = datetime.strptime(day_data['date'], '%Y-%m-%d').date()
            
            # Create StockPrice object
            stock_price = StockPrice(
                ticker=ticker,
                date=price_date,
                open_price=float(day_data.get('open', 0)),
                close_price=float(day_data.get('close', 0)),
                high_price=float(day_data.get('high', 0)),
                low_price=float(day_data.get('low', 0)),
                volume=float(day_data.get('volume', 0))
            )
            
            session.merge(stock_price)  # Use merge to handle duplicates
            session.commit()
            saved_count += 1
            
        except Exception as e:
            print(f"Error saving stock price for {ticker} on {day_data.get('date', 'unknown')}: {e}")
            session.rollback()
            continue
    
    return saved_count



def main():
    """
    Main function to backfill simulation data
    """
    print("Starting backfill process for June 2025...")
    print(f"Processing {len(SP500_TICKERS)} tickers")
    
    # Get database session
    session = get_db_session()
    
    try:
        print("Processing news data for June 2025...")
        
        # First, fetch stock prices for all tickers for the entire month
        # This is more efficient than daily requests
        print("\n=== FETCHING STOCK PRICE DATA ===")
        from_date = "2025-07-01"
        to_date = "2025-07-31"
        
        total_stock_records = 0
        for i, ticker in enumerate(SP500_TICKERS, 1):
            print(f"[{i}/{len(SP500_TICKERS)}] Processing stock prices for {ticker}")
            
            price_data = fetch_stock_prices(ticker, from_date, to_date)
            if price_data:
                saved_count = save_stock_prices_to_db(session, ticker, price_data)
                total_stock_records += saved_count
                print(f"  Saved {saved_count} price records for {ticker}")
        
        print(f"\nTotal stock price records saved: {total_stock_records}")
        
        # Fetch news data for each ticker for the entire month
        print("\n=== FETCHING NEWS DATA ===")
        total_news_articles = 0
        
        # Date range for the entire month of June 2025
        from_date = "2025-07-01"
        to_date = "2025-07-31"
        
        for ticker_idx, ticker in enumerate(SP500_TICKERS, 1):
            print(f"\n[{ticker_idx}/{len(SP500_TICKERS)}] Processing {ticker} for June 2025")
            
            # Fetch all news articles for this ticker for the entire month using pagination
            ticker_news_count = 0
            offset = 0
            limit = 1000
            
            while True:
                news_data = fetch_news_for_ticker(ticker, from_date, to_date, limit=limit, offset=offset)
                
                if not news_data:  # No more articles available
                    break
                
                # Use a representative date for the parsing function, but the actual article dates will be used
                # The parse_article_date function will extract the real publish date from each article
                representative_date = date(2025, 6, 1)  # Only used as fallback if no date in article
                saved_count = save_news_to_db(session, news_data, representative_date)
                ticker_news_count += saved_count
                total_news_articles += saved_count
                
                print(f"    Batch: saved {saved_count} articles (total for {ticker}: {ticker_news_count})")
                
                # If we got fewer articles than the limit, we've reached the end
                if len(news_data) < limit:
                    break
                    
                offset += limit  # Move to next batch
            
            print(f"  Total saved for {ticker}: {ticker_news_count} articles")
            
            # Add a delay between ticker requests to be respectful to API
            # time.sleep(0.1)
        
        print(f"\nTotal news articles saved: {total_news_articles}")
        print("\nNews backfill process completed successfully!")
        
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except Exception as e:
        print(f"Error during backfill process: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    main()
