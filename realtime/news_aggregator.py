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
from newsapi import NewsApiClient
import finnhub
from polygon import RESTClient
from models.database import get_db_session, News
from sqlalchemy import and_

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealtimeNewsAggregator:
    def __init__(self):
        """Initialize all news API clients"""
        # API Keys - should be set as environment variables
        self.alpha_vantage_key = os.getenv('ALPHA_VANTAGE_API_KEY', 'KWL2J50Q32KS3YSM')
        self.newsapi_key = os.getenv('NEWSAPI_KEY')  # Get from newsapi.org
        # Use the same Finnhub API key as in the working fetcher
        self.finnhub_key = os.getenv('FINNHUB_KEY', 'd0p1oc1r01qr8ds0v5j0d0p1oc1r01qr8ds0v5jg')
        self.polygon_key = os.getenv('POLYGON_KEY')  # Get from polygon.io
        self.fmp_key = os.getenv('FMP_KEY')  # Get from financialmodelingprep.com
        # NewsAPI.ai key
        self.newsapi_ai_key = os.getenv('NEWSAPI_AI_KEY', '212a2fe8-6829-4fd4-adac-8d0d649c68f7')
        
        # Initialize API clients
        self.newsapi = NewsApiClient(api_key=self.newsapi_key) if self.newsapi_key else None
        self.finnhub_client = finnhub.Client(api_key=self.finnhub_key)  # Always initialize with fallback key
        self.polygon_client = RESTClient(self.polygon_key) if self.polygon_key else None
        
        self.db_session = get_db_session()
        
        # Financial news sources for NewsAPI
        self.financial_sources = [
            'bloomberg', 'cnbc', 'reuters', 'financial-times', 'the-wall-street-journal',
            'marketwatch', 'yahoo-finance', 'business-insider'
        ]

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

    def fetch_alpha_vantage_news(self, start_time: datetime, end_time: datetime) -> int:
        """Fetch news from Alpha Vantage News & Sentiments API for all tickers and save directly to DB"""
        total_saved = 0
        
        if not self.alpha_vantage_key:
            logger.warning("Alpha Vantage API key not provided")
            return total_saved
            
        # Use the same ticker list as Finnhub and NewsAPI.ai for consistency
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
            logger.info(f"Fetching Alpha Vantage news for {len(tickers)} tickers")
            
            for i, ticker in enumerate(tickers, 1):
                try:
                    logger.info(f"Processing ticker {i}/{len(tickers)}: {ticker}")
                    
                    # Alpha Vantage News & Sentiments API - ticker-specific news
                    url = "https://www.alphavantage.co/query"
                    params = {
                        'function': 'NEWS_SENTIMENT',
                        'tickers': ticker,
                        'apikey': self.alpha_vantage_key,
                        'limit': 50,
                        'time_from': start_time.strftime('%Y%m%dT%H%M'),
                        'time_to': end_time.strftime('%Y%m%dT%H%M')
                    }
                    
                    response = requests.get(url, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        logger.debug(f"  Response status: {response.status_code}, Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                        
                        ticker_saved = 0
                        if 'feed' in data and isinstance(data['feed'], list):
                            logger.info(f"  Got {len(data['feed'])} articles for {ticker}")
                            
                            for article in data['feed']:
                                try:
                                    # Parse publication date from Alpha Vantage format
                                    time_published_str = article.get('time_published', '')
                                    if not time_published_str:
                                        logger.debug(f"  Skipping article without time_published: {article.get('title', 'No title')[:50]}...")
                                        continue
                                    
                                    # Parse Alpha Vantage datetime format (YYYYMMDDTHHMMSS)
                                    try:
                                        published = datetime.strptime(time_published_str, '%Y%m%dT%H%M%S')
                                        published = published.replace(tzinfo=pytz.UTC)  # Alpha Vantage times are in UTC
                                    except ValueError as ve:
                                        logger.warning(f"  Failed to parse time_published '{time_published_str}' for article: {ve}")
                                        continue
                                    
                                    # Ensure we have timezone-aware times for comparison
                                    start_compare = start_time.replace(tzinfo=pytz.UTC) if start_time.tzinfo is None else start_time
                                    end_compare = end_time.replace(tzinfo=pytz.UTC) if end_time.tzinfo is None else end_time
                                    
                                    # Check if article is within our time range
                                    if start_compare <= published <= end_compare:
                                        # Get article content
                                        title = article.get('title', '')
                                        summary = article.get('summary', '')
                                        url = article.get('url', '')
                                        source = article.get('source', 'Alpha Vantage')
                                        
                                        if not title:
                                            logger.debug(f"  Skipping article without title")
                                            continue
                                        
                                        # Save directly to database
                                        try:
                                            news_item = News(
                                                title=title[:500],  # Truncate if too long
                                                summary=summary[:1000] if summary else '',  # Truncate if too long
                                                source=f"{source} ({ticker})",
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
                                    logger.warning(f"  Error processing article for {ticker}: {e}")
                                    continue
                        else:
                            logger.info(f"  No articles found for {ticker} (no 'feed' in response or empty)")
                    else:
                        logger.warning(f"  Alpha Vantage request failed for {ticker}: {response.status_code}")
                        if response.status_code == 429:
                            logger.warning("  Rate limit exceeded, waiting longer...")
                            time.sleep(5)  # Wait longer on rate limit
                    
                    total_saved += ticker_saved
                    logger.info(f"  Saved {ticker_saved} new articles for {ticker}")
                    
                    # Rate limiting: Alpha Vantage allows 75 calls/minute for free tier
                    # 75 calls/minute = 0.8 seconds between calls, use 0.85 to be safe
                    time.sleep(0.85)
                    
                except Exception as e:
                    logger.error(f"Error fetching Alpha Vantage news for {ticker}: {e}")
                    continue
                    
            logger.info(f"Total saved: {total_saved} articles from Alpha Vantage")
                    
        except Exception as e:
            logger.error(f"Error fetching Alpha Vantage news: {e}")
            
        return total_saved

    def fetch_newsapi_news(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Fetch financial news from NewsAPI"""
        news_articles = []
        
        if not self.newsapi:
            logger.warning("NewsAPI client not initialized - missing API key")
            return news_articles
            
        try:
            # Financial keywords
            queries = [
                'stock market OR stocks OR trading OR NYSE OR NASDAQ',
                'earnings OR financial results OR quarterly report',
                'merger OR acquisition OR IPO',
                'Federal Reserve OR interest rates OR inflation'
            ]
            
            for query in queries:
                articles = self.newsapi.get_everything(
                    q=query,
                    sources=','.join(self.financial_sources),  
                    from_param=start_time.strftime('%Y-%m-%d'),
                    to=end_time.strftime('%Y-%m-%d'),
                    language='en',
                    sort_by='publishedAt',
                    page_size=25
                )
                
                if articles['status'] == 'ok':
                    for article in articles['articles']:
                        published = datetime.strptime(article['publishedAt'], '%Y-%m-%dT%H:%M:%SZ')
                        if start_time <= published <= end_time:
                            news_articles.append({
                                'title': article.get('title', ''),
                                'summary': article.get('description', ''),
                                'source': article.get('source', {}).get('name', 'NewsAPI'),
                                'url': article.get('url', ''),
                                'time_published': published,
                                'api_source': 'newsapi'
                            })
                
                time.sleep(1)  # Rate limiting
                
        except Exception as e:
            logger.error(f"Error fetching NewsAPI news: {e}")
            
        return news_articles

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

    def fetch_polygon_news(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Fetch news from Polygon.io"""
        news_articles = []
        
        if not self.polygon_client:
            logger.warning("Polygon client not initialized - missing API key")
            return news_articles
            
        try:
            # Polygon news ticker endpoint
            news = self.polygon_client.list_ticker_news(
                published_utc_gte=start_time.strftime('%Y-%m-%d'),
                published_utc_lte=end_time.strftime('%Y-%m-%d'),
                limit=50,
                order='desc'
            )
            
            for article in news:
                published = datetime.strptime(article.published_utc, '%Y-%m-%dT%H:%M:%SZ')
                if start_time <= published <= end_time:
                    news_articles.append({
                        'title': article.title,
                        'summary': getattr(article, 'description', ''),
                        'source': getattr(article, 'publisher', {}).get('name', 'Polygon'),
                        'url': article.article_url,
                        'time_published': published,
                        'api_source': 'polygon'
                    })
                    
        except Exception as e:
            logger.error(f"Error fetching Polygon news: {e}")
            
        return news_articles

    def fetch_fmp_news(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Fetch news from Financial Modeling Prep"""
        news_articles = []
        
        if not self.fmp_key:
            logger.warning("FMP API key not provided")
            return news_articles
            
        try:
            # Major tickers to get news for
            tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'JNJ', 'V']
            
            for ticker in tickers:
                url = f"https://financialmodelingprep.com/api/v3/stock_news"
                params = {
                    'tickers': ticker,
                    'from': start_time.strftime('%Y-%m-%d'),
                    'to': end_time.strftime('%Y-%m-%d'), 
                    'apikey': self.fmp_key,
                    'limit': 10
                }
                
                response = requests.get(url, params=params)
                data = response.json()
                
                if isinstance(data, list):
                    for article in data:
                        published = datetime.strptime(article['publishedDate'], '%Y-%m-%d %H:%M:%S')
                        if start_time <= published <= end_time:
                            news_articles.append({
                                'title': article.get('title', ''),
                                'summary': article.get('text', ''),
                                'source': article.get('site', 'FMP'),
                                'url': article.get('url', ''),
                                'time_published': published,
                                'api_source': 'fmp'
                            })
                
                time.sleep(0.5)  # Rate limiting
                
        except Exception as e:
            logger.error(f"Error fetching FMP news: {e}")
            
        return news_articles

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
        
        # Add Alpha Vantage as tertiary source for ticker-specific news with sentiment
        try:
            logger.info("Fetching from Alpha Vantage ticker news (TERTIARY SOURCE)...")
            alpha_vantage_saved = self.fetch_alpha_vantage_news_only(start_time, end_time)
            total_saved += alpha_vantage_saved
            logger.info(f"Saved {alpha_vantage_saved} articles from Alpha Vantage")
        except Exception as e:
            logger.error(f"Failed to fetch from Alpha Vantage: {e}")
        
        logger.info(f"Total articles saved to database: {total_saved}")
        return total_saved

    def store_news_in_db(self, news_articles: List[Dict]):
        """Store fetched news in database"""
        stored_count = 0
        
        for article in news_articles:
            try:
                # Check if article already exists
                existing = self.db_session.query(News).filter(
                    News.url == article['url']
                ).first()
                
                if not existing and article['url']:  # Only store if URL exists and not duplicate
                    news_item = News(
                        title=article['title'][:500],  # Truncate if too long
                        summary=article['summary'][:1000] if article['summary'] else '',
                        source=article['source'],
                        url=article['url'],
                        time_published=article['time_published']
                    )
                    self.db_session.add(news_item)
                    stored_count += 1
            except Exception as e:
                logger.error(f"Error storing news article: {e}")
                continue
        
        try:
            self.db_session.commit()
            logger.info(f"Stored {stored_count} new articles in database")
        except Exception as e:
            logger.error(f"Error committing to database: {e}")
            self.db_session.rollback()

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

    def fetch_alpha_vantage_news_only(self, start_time: datetime, end_time: datetime) -> int:
        """Fetch and save only Alpha Vantage news (already saves directly to DB)"""
        return self.fetch_alpha_vantage_news(start_time, end_time)

    def fetch_newsapi_news_only(self, start_time: datetime, end_time: datetime) -> int:
        """Fetch and save only NewsAPI.org news"""
        news_articles = self.fetch_newsapi_news(start_time, end_time)
        self.store_news_in_db(news_articles)
        return len(news_articles)

    def fetch_polygon_news_only(self, start_time: datetime, end_time: datetime) -> int:
        """Fetch and save only Polygon news"""
        news_articles = self.fetch_polygon_news(start_time, end_time)
        self.store_news_in_db(news_articles)
        return len(news_articles)

    def fetch_fmp_news_only(self, start_time: datetime, end_time: datetime) -> int:
        """Fetch and save only FMP news"""
        news_articles = self.fetch_fmp_news(start_time, end_time)
        self.store_news_in_db(news_articles)
        return len(news_articles)

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