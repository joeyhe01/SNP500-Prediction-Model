#!/usr/bin/env python3
"""
Realtime News Aggregator for Trading Predictions
Combines multiple news APIs to get comprehensive coverage
"""

import os
import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import pytz
import finnhub
from models.database import get_db_session, News
from sqlalchemy import and_

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealtimeNewsAggregator:
    def __init__(self):
        """Initialize all news API clients"""
        # API Keys - should be set as environment variables
        # Use the same Finnhub API key as in the working fetcher
        self.finnhub_key = os.getenv('FINNHUB_KEY', 'd0p1oc1r01qr8ds0v5j0d0p1oc1r01qr8ds0v5jg')
        # NewsAPI.ai key
        self.newsapi_ai_key = os.getenv('NEWSAPI_AI_KEY', '212a2fe8-6829-4fd4-adac-8d0d649c68f7')
        
        # Initialize API clients
        self.finnhub_client = finnhub.Client(api_key=self.finnhub_key)  # Always initialize with fallback key
        
        self.db_session = get_db_session()

    def get_time_range(self):
        """
        Get the time range: previous day 5PM to current day 9AM or current time (whichever is earlier)
        """
        now = datetime.now()
        current_time = now.time()
        
        # If it's before 9 AM today, get from yesterday 5PM to now
        if current_time < datetime.strptime('09:00', '%H:%M').time():
            end_time = now
            start_time = now.replace(hour=17, minute=0, second=0, microsecond=0) - timedelta(days=1)
        else:
            # If it's after 9 AM, get from yesterday 5PM to current time
            start_time = now.replace(hour=17, minute=0, second=0, microsecond=0) - timedelta(days=1)
            end_time = now
            
        # Skip weekends for start_time
        while start_time.weekday() > 4:  # Saturday=5, Sunday=6
            start_time = start_time - timedelta(days=1)
            
        logger.info(f"News time range: {start_time} to {end_time}")
        return start_time, end_time



    def fetch_finnhub_news(self, start_time: datetime, end_time: datetime) -> int:
        """Fetch company-specific news from Finnhub for all tickers and save directly to DB"""
        total_saved = 0
        
        if not self.finnhub_client:
            logger.warning("Finnhub client not initialized - missing API key")
            return total_saved
            
        # All tickers from the sentiment model
        tickers = [
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
        ]
        
        try:
            # Convert to YYYY-MM-DD format for Finnhub API
            from_date = start_time.strftime('%Y-%m-%d')
            to_date = end_time.strftime('%Y-%m-%d')
            
            logger.info(f"Fetching Finnhub company news for {len(tickers)} tickers from {from_date} to {to_date}")
            
            for i, ticker in enumerate(tickers, 1):
                try:
                    logger.info(f"Processing ticker {i}/{len(tickers)}: {ticker}")
                    
                    # Use the company news endpoint
                    news = self.finnhub_client.company_news(ticker, _from=from_date, to=to_date)
                    
                    logger.info(f"  Got {len(news) if news else 0} articles for {ticker}")
                    
                    ticker_saved = 0
                    if news:  # Check if news is not None or empty
                        for article in news:
                            try:
                                # Convert Unix timestamp to timezone-aware UTC datetime
                                published = datetime.fromtimestamp(article['datetime'], tz=pytz.UTC)
                                
                                # Ensure we have timezone-aware times for comparison (without modifying originals)
                                start_compare = start_time.replace(tzinfo=pytz.UTC) if start_time.tzinfo is None else start_time
                                end_compare = end_time.replace(tzinfo=pytz.UTC) if end_time.tzinfo is None else end_time
                                
                                # Check if article is within our time range
                                if start_compare <= published <= end_compare:
                                    # Save directly to database
                                    try:
                                        news_item = News(
                                            title=article.get('headline', '')[:500],  # Truncate if too long
                                            summary=article.get('summary', '')[:1000] if article.get('summary') else '',
                                            source=article.get('source', 'Finnhub'),
                                            url=article.get('url', ''),
                                            time_published=published
                                        )
                                        self.db_session.add(news_item)
                                        self.db_session.commit()  # Commit immediately
                                        ticker_saved += 1
                                    except Exception as db_e:
                                        # Unique constraint violation or other DB error - skip this article
                                        self.db_session.rollback()
                                        continue
                                        
                            except Exception as e:
                                logger.warning(f"  Error processing article for {ticker}: {e}")
                                continue
                    
                    total_saved += ticker_saved
                    logger.info(f"  Saved {ticker_saved} new articles for {ticker}")
                    
                    # Rate limiting - Finnhub allows 60 calls/minuite
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error fetching news for {ticker}: {e}")
                    continue
                    
            logger.info(f"Total saved: {total_saved} articles from Finnhub company news")
                    
        except Exception as e:
            logger.error(f"Error fetching Finnhub company news: {e}")
            
        return total_saved

    def fetch_newsapi_ai_news(self, start_time: datetime, end_time: datetime) -> int:
        """Fetch news from NewsAPI.ai for all tickers and save directly to DB"""
        total_saved = 0
        
        if not self.newsapi_ai_key:
            logger.warning("NewsAPI.ai API key not provided")
            return total_saved
            
        # Ticker to company name mapping for better news search
        ticker_to_company = {
            'AAPL': 'Apple',
            'MSFT': 'Microsoft',
            'GOOGL': 'Google Alphabet',
            'AMZN': 'Amazon',
            'META': 'Meta Facebook',
            'TSLA': 'Tesla',
            'NVDA': 'NVIDIA',
            'JPM': 'JPMorgan Chase',
            'JNJ': 'Johnson & Johnson',
            'V': 'Visa',
            'PG': 'Procter & Gamble',
            'UNH': 'UnitedHealth',
            'HD': 'Home Depot',
            'MA': 'Mastercard',
            'DIS': 'Disney',
            'BAC': 'Bank of America',
            'NFLX': 'Netflix',
            'ADBE': 'Adobe',
            'CRM': 'Salesforce',
            'PFE': 'Pfizer',
            'CSCO': 'Cisco',
            'INTC': 'Intel',
            'WMT': 'Walmart',
            'IBM': 'IBM',
            'BA': 'Boeing',
            'GS': 'Goldman Sachs',
            'MS': 'Morgan Stanley',
            'CVX': 'Chevron',
            'XOM': 'ExxonMobil',
            'VZ': 'Verizon',
            'T': 'AT&T',
            'KO': 'Coca-Cola',
            'PEP': 'PepsiCo',
            'NKE': 'Nike',
            'MRK': 'Merck',
            'ABBV': 'AbbVie',
            'TMO': 'Thermo Fisher',
            'COST': 'Costco',
            'AVGO': 'Broadcom',
            'ORCL': 'Oracle',
            'ACN': 'Accenture',
            'LLY': 'Eli Lilly',
            'TXN': 'Texas Instruments',
            'MCD': 'McDonald\'s',
            'QCOM': 'Qualcomm',
            'DHR': 'Danaher',
            'NEE': 'NextEra Energy',
            'BMY': 'Bristol Myers Squibb',
            'UPS': 'UPS',
            'RTX': 'Raytheon',
            'LOW': 'Lowe\'s',
            'SPGI': 'S&P Global',
            'INTU': 'Intuit',
            'AMD': 'AMD',
            'CAT': 'Caterpillar',
            'MDLZ': 'Mondelez',
            'GE': 'General Electric',
            'MMM': '3M',
            'CVS': 'CVS Health',
            'AMT': 'American Tower',
            'AXP': 'American Express',
            'DE': 'Deere',
            'BKNG': 'Booking Holdings',
            'AMAT': 'Applied Materials',
            'TJX': 'TJX Companies',
            'ISRG': 'Intuitive Surgical',
            'ADP': 'ADP',
            'GILD': 'Gilead Sciences',
            'CME': 'CME Group',
            'TMUS': 'T-Mobile',
            'REGN': 'Regeneron',
            'C': 'Citigroup',
            'VRTX': 'Vertex Pharmaceuticals',
            'BLK': 'BlackRock',
            'ZTS': 'Zoetis',
            'NOW': 'ServiceNow',
            'PANW': 'Palo Alto Networks',
            'SYK': 'Stryker',
            'BSX': 'Boston Scientific',
            'SNOW': 'Snowflake',
            'UBER': 'Uber',
            'SBUX': 'Starbucks',
            'SPOT': 'Spotify',
            'ABNB': 'Airbnb',
            'PYPL': 'PayPal',
            'SQ': 'Block Square',
            'COIN': 'Coinbase',
            'ROKU': 'Roku',
            'ZM': 'Zoom',
            'DOCU': 'DocuSign',
            'ETSY': 'Etsy',
            'SHOP': 'Shopify',
            'TWLO': 'Twilio',
            'SNAP': 'Snapchat',
            'PINS': 'Pinterest',
            'LYFT': 'Lyft',
            'DBX': 'Dropbox',
            'W': 'Wayfair',
            'PTON': 'Peloton',
            'HOOD': 'Robinhood',
            'F': 'Ford',
            'GM': 'General Motors',
            'RIVN': 'Rivian',
            'LCID': 'Lucid Motors',
            'NIO': 'NIO',
            'LI': 'Li Auto',
            'XPEV': 'XPeng',
            'PLTR': 'Palantir',
            'NET': 'Cloudflare',
            'DDOG': 'Datadog',
            'CRWD': 'CrowdStrike',
            'OKTA': 'Okta',
            'MDB': 'MongoDB',
            'TEAM': 'Atlassian',
            'FTNT': 'Fortinet',
            'WDAY': 'Workday',
            'ADSK': 'Autodesk',
            'EA': 'Electronic Arts',
            'TTWO': 'Take-Two Interactive',
            'ATVI': 'Activision Blizzard',
            'RBLX': 'Roblox',
            'U': 'Unity',
            'MSCI': 'MSCI',
            'MCO': 'Moody\'s',
            'ICE': 'Intercontinental Exchange',
            'NDAQ': 'Nasdaq',
            'CBOE': 'Cboe Global Markets',
            'WFC': 'Wells Fargo',
            'USB': 'US Bancorp',
            'PNC': 'PNC Financial',
            'TFC': 'Truist Financial',
            'SCHW': 'Charles Schwab',
            'COF': 'Capital One',
            'AIG': 'AIG',
            'MET': 'MetLife',
            'PRU': 'Prudential',
            'TRV': 'Travelers',
            'AFL': 'Aflac',
            'ALL': 'Allstate',
            'PGR': 'Progressive',
            'CB': 'Chubb',
            'HIG': 'Hartford Financial',
            'WBA': 'Walgreens',
            'CI': 'Cigna',
            'HUM': 'Humana',
            'CNC': 'Centene',
            'ELV': 'Elevance Health'
        }
        
        try:
            logger.info(f"Fetching NewsAPI.ai news for {len(ticker_to_company)} companies")
            
            for i, (ticker, company_name) in enumerate(ticker_to_company.items(), 1):
                try:
                    logger.info(f"Processing {i}/{len(ticker_to_company)}: {ticker} ({company_name})")
                    
                    # NewsAPI.ai searchArticles endpoint
                    url = "https://eventregistry.org/api/v1/article/getArticles"
                    
                    # Alternative approach - use direct API call
                    headers = {
                        'Content-Type': 'application/json'
                    }
                    
                    # Try a direct HTTP request to NewsAPI.ai using company name as keyword
                    params = {
                        'action': 'getArticles',
                        'keyword': company_name,
                        'articlesPage': 1,
                        'articlesCount': 100,
                        'articlesSortBy': 'date',
                        'lang': 'eng',
                        'apiKey': self.newsapi_ai_key
                    }
                    
                    response = requests.get('https://newsapi.ai/api/v1/article/getArticles', params=params, headers=headers)
                    
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"  Response status: {response.status_code}, Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                        
                        # Parse articles based on actual NewsAPI.ai response structure
                        articles = []
                        if isinstance(data, dict) and 'articles' in data and 'results' in data['articles']:
                            articles = data['articles']['results']
                            total_results = data['articles'].get('totalResults', 0)
                            logger.info(f"  NewsAPI.ai returned {len(articles)} articles out of {total_results} total for {company_name}")
                        else:
                            logger.warning(f"  Unexpected response structure for {company_name}: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                        
                        ticker_saved = 0
                        for article in articles:
                            try:
                                # Parse publication date - NewsAPI.ai uses dateTime in UTC format
                                date_str = article.get('dateTime')
                                if not date_str:
                                    logger.debug(f"  Skipping article without dateTime: {article.get('title', 'No title')[:50]}...")
                                    continue
                                
                                # Parse UTC datetime (format: "2023-05-16T10:35:00Z")
                                try:
                                    if date_str.endswith('Z'):
                                        # Remove Z and add UTC timezone
                                        published = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                                    else:
                                        # Assume UTC if no timezone info
                                        published = datetime.fromisoformat(date_str).replace(tzinfo=pytz.UTC)
                                except ValueError as ve:
                                    logger.warning(f"  Failed to parse dateTime '{date_str}' for article: {ve}")
                                    continue
                                
                                # Ensure we have timezone-aware times for comparison
                                start_compare = start_time.replace(tzinfo=pytz.UTC) if start_time.tzinfo is None else start_time
                                end_compare = end_time.replace(tzinfo=pytz.UTC) if end_time.tzinfo is None else end_time
                                
                                # Check if article is within our time range
                                if start_compare <= published <= end_compare:
                                    # Extract source information
                                    source_info = article.get('source', {})
                                    source_title = source_info.get('title', 'NewsAPI.ai') if isinstance(source_info, dict) else 'NewsAPI.ai'
                                    
                                    # Get article content
                                    title = article.get('title', '')
                                    body = article.get('body', '')
                                    url = article.get('url', '')
                                    
                                    if not title:
                                        logger.debug(f"  Skipping article without title")
                                        continue
                                    
                                    # Save directly to database
                                    try:
                                        news_item = News(
                                            title=title[:500],  # Truncate if too long
                                            summary=body[:1000] if body else '',  # Truncate if too long
                                            source=f"{source_title} ({company_name})",
                                            url=url,
                                            time_published=published  # Already in UTC
                                        )
                                        self.db_session.add(news_item)
                                        self.db_session.commit()  # Commit immediately
                                        ticker_saved += 1
                                        logger.debug(f"    Saved article: {title[:60]}...")
                                    except Exception as db_e:
                                        # Unique constraint violation or other DB error - skip this article
                                        self.db_session.rollback()
                                        logger.debug(f"    Skipped duplicate article: {title[:60]}...")
                                        continue
                                else:
                                    logger.debug(f"  Article outside time range: {published} not in [{start_compare}, {end_compare}]")
                                        
                            except Exception as e:
                                logger.warning(f"  Error processing article for {company_name} ({ticker}): {e}")
                                continue
                    else:
                        logger.warning(f"  NewsAPI.ai request failed for {company_name} ({ticker}): {response.status_code}")
                    
                    total_saved += ticker_saved
                    logger.info(f"  Saved {ticker_saved} new articles for {company_name} ({ticker})")
                    
                    # Rate limiting - be conservative with NewsAPI.ai
                    time.sleep(1.5)
                    
                except Exception as e:
                    logger.error(f"Error fetching NewsAPI.ai news for {company_name} ({ticker}): {e}")
                    continue
                    
            logger.info(f"Total saved: {total_saved} articles from NewsAPI.ai")
                    
        except Exception as e:
            logger.error(f"Error fetching NewsAPI.ai news: {e}")
            
        return total_saved

    def aggregate_all_news(self) -> int:
        """Fetch and save news directly to database, prioritizing Finnhub company news"""
        start_time, end_time = self.get_time_range()
        return self._aggregate_news_for_range(start_time, end_time)
    
    def aggregate_all_news_custom_range(self, start_time: datetime, end_time: datetime) -> int:
        """Fetch and save news directly to database for a custom time range"""
        return self._aggregate_news_for_range(start_time, end_time)
    
    def _aggregate_news_for_range(self, start_time: datetime, end_time: datetime) -> int:
        """Private method to fetch and save news for a specific time range"""
        total_saved = 0
        
        logger.info(f"Starting news aggregation for range: {start_time} to {end_time}")
        
        # Prioritize Finnhub company news as the main source for ticker-specific news
        try:
            logger.info("Fetching from Finnhub company news (PRIMARY SOURCE)...")
            finnhub_saved = self.fetch_finnhub_news(start_time, end_time)
            total_saved += finnhub_saved
            logger.info(f"Saved {finnhub_saved} articles from Finnhub company news")
        except Exception as e:
            logger.error(f"Failed to fetch from Finnhub: {e}")
        
        # Add NewsAPI.ai as secondary source for company-specific news
        try:
            logger.info("Fetching from NewsAPI.ai company news (SECONDARY SOURCE)...")
            newsapi_ai_saved = self.fetch_newsapi_ai_news(start_time, end_time)
            total_saved += newsapi_ai_saved
            logger.info(f"Saved {newsapi_ai_saved} articles from NewsAPI.ai")
        except Exception as e:
            logger.error(f"Failed to fetch from NewsAPI.ai: {e}")
        
        logger.info(f"Total articles saved to database: {total_saved}")
        return total_saved

    def run_realtime_aggregation(self):
        """Main method to run the realtime news aggregation"""
        logger.info("Starting realtime news aggregation...")
        
        # Aggregate and save news directly to database
        total_saved = self.aggregate_all_news()
        
        logger.info(f"Realtime aggregation completed: {total_saved} articles saved to database")
        
        return total_saved

    def close(self):
        """Close database session"""
        self.db_session.close()



    def fetch_finnhub_news_only(self, start_time: datetime, end_time: datetime) -> int:
        """Fetch and save only Finnhub news (already saves directly to DB)"""
        return self.fetch_finnhub_news(start_time, end_time)

    def fetch_newsapi_ai_news_only(self, start_time: datetime, end_time: datetime) -> int:
        """Fetch and save only NewsAPI.ai news (already saves directly to DB)"""
        return self.fetch_newsapi_ai_news(start_time, end_time)

if __name__ == "__main__":
    # Test the aggregator
    aggregator = RealtimeNewsAggregator()
    try:
        articles = aggregator.run_realtime_aggregation()
        print(f"Successfully aggregated {articles} articles")
    finally:
        aggregator.close() 