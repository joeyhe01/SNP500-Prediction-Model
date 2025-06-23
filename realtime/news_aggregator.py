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
        self.finnhub_key = os.getenv('FINNHUB_KEY')  # Get from finnhub.io
        self.polygon_key = os.getenv('POLYGON_KEY')  # Get from polygon.io
        self.fmp_key = os.getenv('FMP_KEY')  # Get from financialmodelingprep.com
        
        # Initialize API clients
        self.newsapi = NewsApiClient(api_key=self.newsapi_key) if self.newsapi_key else None
        self.finnhub_client = finnhub.Client(api_key=self.finnhub_key) if self.finnhub_key else None
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

    def fetch_alpha_vantage_news(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Fetch news from Alpha Vantage News & Sentiments API"""
        news_articles = []
        
        try:
            # Alpha Vantage News & Sentiments API - focused on most relevant topics
            topics = ['financial_markets', 'earnings']  # Reduced from 4 to 2 topics for faster fetching
            
            for topic in topics:
                url = f"https://www.alphavantage.co/query"
                params = {
                    'function': 'NEWS_SENTIMENT',
                    'topics': topic,
                    'apikey': self.alpha_vantage_key,
                    'limit': 50,
                    'time_from': start_time.strftime('%Y%m%dT%H%M'),
                    'time_to': end_time.strftime('%Y%m%dT%H%M')
                }
                
                response = requests.get(url, params=params)
                data = response.json()
                
                if 'feed' in data:
                    for article in data['feed']:
                        news_articles.append({
                            'title': article.get('title', ''),
                            'summary': article.get('summary', ''),
                            'source': article.get('source', 'Alpha Vantage'),
                            'url': article.get('url', ''),
                            'time_published': datetime.strptime(article.get('time_published', ''), '%Y%m%dT%H%M%S'),
                            'api_source': 'alpha_vantage'
                        })
                
                # Optimized rate limiting: 75 calls/minute = 0.8 seconds between calls
                time.sleep(0.85)  # Slightly conservative to avoid hitting limits
                
        except Exception as e:
            logger.error(f"Error fetching Alpha Vantage news: {e}")
            
        return news_articles

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

    def fetch_finnhub_news(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Fetch news from Finnhub"""
        news_articles = []
        
        if not self.finnhub_client:
            logger.warning("Finnhub client not initialized - missing API key")
            return news_articles
            
        try:
            # Convert to Unix timestamp
            start_unix = int(start_time.timestamp())
            end_unix = int(end_time.timestamp())
            
            # General market news
            news = self.finnhub_client.general_news('general', min_id=0)
            
            for article in news:
                published = datetime.fromtimestamp(article['datetime'])
                if start_time <= published <= end_time:
                    news_articles.append({
                        'title': article.get('headline', ''),
                        'summary': article.get('summary', ''),
                        'source': article.get('source', 'Finnhub'),
                        'url': article.get('url', ''),
                        'time_published': published,
                        'api_source': 'finnhub'
                    })
                    
        except Exception as e:
            logger.error(f"Error fetching Finnhub news: {e}")
            
        return news_articles

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

    def aggregate_all_news(self) -> List[Dict]:
        """Aggregate news from all available APIs"""
        start_time, end_time = self.get_time_range()
        all_news = []
        
        logger.info("Starting news aggregation from multiple APIs...")
        
        # Fetch from all APIs
        apis = [
            ('Alpha Vantage', self.fetch_alpha_vantage_news),
            ('NewsAPI', self.fetch_newsapi_news),
            ('Finnhub', self.fetch_finnhub_news),
            ('Polygon', self.fetch_polygon_news), 
            ('FMP', self.fetch_fmp_news)
        ]
        
        for api_name, fetch_func in apis:
            try:
                logger.info(f"Fetching from {api_name}...")
                articles = fetch_func(start_time, end_time)
                all_news.extend(articles)
                logger.info(f"Fetched {len(articles)} articles from {api_name}")
            except Exception as e:
                logger.error(f"Failed to fetch from {api_name}: {e}")
        
        # Remove duplicates based on URL and title
        unique_news = []
        seen_urls = set()
        seen_titles = set()
        
        for article in all_news:
            url = article.get('url', '')
            title = article.get('title', '')
            
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_news.append(article)
            elif title and title not in seen_titles:
                seen_titles.add(title)
                unique_news.append(article)
        
        logger.info(f"Total unique articles: {len(unique_news)}")
        return unique_news

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
        
        # Aggregate news from all APIs
        news_articles = self.aggregate_all_news()
        
        # Store in database
        if news_articles:
            self.store_news_in_db(news_articles)
        else:
            logger.info("No news articles found for the specified time range")
        
        return news_articles

    def close(self):
        """Close database session"""
        self.db_session.close()

if __name__ == "__main__":
    # Test the aggregator
    aggregator = RealtimeNewsAggregator()
    try:
        articles = aggregator.run_realtime_aggregation()
        print(f"Successfully aggregated {len(articles)} articles")
    finally:
        aggregator.close() 