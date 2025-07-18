import os
import json
import time
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from openai import OpenAI
import openai
from models.database import get_db_session, News, NewsSentiment
from sqlalchemy import and_, or_
import logging

# Import vector search for RAG functionality
from models.vector_db import search_news, initialize_vector_search

logger = logging.getLogger(__name__)

class LLMSentimentModel:
    def __init__(self, debug=False):
        """Initialize the LLM sentiment model with OpenAI client"""
        self.debug = debug
        self.session = get_db_session()
        
        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        # api_key = "put key here"
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = OpenAI(api_key=api_key)
        
        # Initialize vector search engine for RAG
        try:
            initialize_vector_search()
            if self.debug:
                print("✓ Vector search engine initialized for RAG")
        except Exception as e:
            if self.debug:
                print(f"⚠ Could not initialize vector search: {e}")
        
        # Common S&P 500 tickers for validation
        self.sp500_tickers = {
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
        
        if self.debug:
            print(f"LLM Sentiment Model initialized with {len(self.sp500_tickers)} known tickers")
    
    def analyze_news_sentiment(self, headline: str, summary: str = None) -> Tuple[List[Dict], List[List]]:
        """
        Use OpenAI with RAG to analyze news sentiment and extract ticker/sentiment pairs
        
        Args:
            headline: News headline text
            summary: News summary text (optional)
            
        Returns:
            Tuple of:
                - List of dictionaries with 'ticker' and 'sentiment' keys
                - List of [faiss_id, similarity_score] pairs for similar articles used as context
        """
        if not headline or not isinstance(headline, str):
            if self.debug:
                print(f"Invalid headline input: {headline}")
            return [], []
        
        try:
            # Prepare the content for analysis
            content = f"Headline: {headline}"
            if summary and isinstance(summary, str) and summary.strip():
                content += f"\n\nSummary: {summary}"
            
            # RAG Enhancement: Query vector database for similar historical articles
            similar_results = search_news(content, k=5)
            
            similar_articles = []
            similar_faiss_ids = []  # Will store tuples of (faiss_id, similarity_score)
            
            for news_record, similarity in similar_results:
                if self.debug:
                    print(f"  Found similar article: '{news_record.title[:80]}...' (similarity: {similarity:.3f})")
                
                if similarity > 0.3:  # Lower threshold for better RAG context
                    similar_articles.append({
                        'title': news_record.title,
                        'description': news_record.description,
                        'date': news_record.date_publish.strftime('%Y-%m-%d'),
                        'ticker_changes': news_record.ticker_metadata,
                        'similarity': similarity
                    })
                    # Store as tuple: (faiss_id, similarity_score)
                    similar_faiss_ids.append([news_record.id, round(similarity, 4)])
            
            if self.debug and similar_articles:
                print(f"Found {len(similar_articles)} similar articles for RAG context")
            
            # Create the RAG-enhanced prompt for OpenAI
            historical_context = ""
            if similar_articles:
                historical_context = "\n\nHISTORICAL CONTEXT - Similar news and market reactions:\n"
                for i, article in enumerate(similar_articles, 1):
                    historical_context += f"   Title: {article['title']}\n"
                    historical_context += f"   Description: {article['description'][:200]}...\n"
                    if article['ticker_changes']:
                        historical_context += f"   Percentage change in price for ticker: {article['ticker_changes']}\n"
                    historical_context += "\n"
                
                historical_context += "Use this historical context to better predict how the market might react to the current news.\n"
            
            prompt = f"""Analyze this financial news and determine which publicly traded companies (stocks) might be affected and how. Use historical market reactions to similar news to inform your analysis.

CURRENT NEWS:
{content}
{historical_context}

Based on the current news and any historical patterns from similar articles above, predict:
1. Which publicly traded companies will be most affected
2. How the market sentiment will likely change for each company
3. Consider both immediate reactions and next-day market movements

Please return a JSON array of objects, where each object has:
- "ticker": The stock ticker symbol (e.g., "AAPL", "GOOGL", "TSLA")
- "sentiment": Either "positive", "negative", or "neutral"

Only include major publicly traded companies that are directly mentioned or significantly affected by this news. Focus on companies that are likely to be in major stock indices like the S&P 500.

If historical similar articles show consistent patterns, factor that into your sentiment analysis. Consider how similar news affected stock prices in the past.

If no specific companies are clearly affected, return an empty array.

Example response format:
[
  {{"ticker": "AAPL", "sentiment": "positive"}},
  {{"ticker": "GOOGL", "sentiment": "negative"}}
]"""

            # Call OpenAI API with retry logic
            max_retries = 5
            retry_count = 0
            response = None
            
            while retry_count <= max_retries:
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-4o-mini",  # Use the more cost-effective model
                        messages=[
                            {"role": "system", "content": "You are a financial analyst expert at identifying how news affects publicly traded companies. You respond only with valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,  # Low temperature for more consistent results
                        max_tokens=500
                    )
                    break  # Success, exit retry loop
                    
                except openai.RateLimitError as e:
                    retry_count += 1
                    if retry_count <= max_retries:
                        if self.debug:
                            print(f"Rate limit error, retry {retry_count}/{max_retries} after 10 seconds: {e}")
                        else:
                            logger.warning(f"Rate limit error, retry {retry_count}/{max_retries} after 10 seconds")
                        time.sleep(10)
                        continue
                    else:
                        if self.debug:
                            print(f"Rate limit error - max retries exceeded: {e}")
                        else:
                            logger.error(f"Rate limit error - max retries exceeded: {e}")
                        return [], similar_faiss_ids
                        
                except (openai.APIError, openai.InternalServerError, openai.APIConnectionError) as e:
                    retry_count += 1
                    if retry_count <= max_retries:
                        if self.debug:
                            print(f"OpenAI API error, retry {retry_count}/{max_retries} after 10 seconds: {e}")
                        else:
                            logger.warning(f"OpenAI API error, retry {retry_count}/{max_retries} after 10 seconds")
                        time.sleep(10)
                        continue
                    else:
                        if self.debug:
                            print(f"OpenAI API error - max retries exceeded: {e}")
                        else:
                            logger.error(f"OpenAI API error - max retries exceeded: {e}")
                        return [], similar_faiss_ids
            
            if response is None:
                if self.debug:
                    print("Failed to get response from OpenAI after retries")
                else:
                    logger.error("Failed to get response from OpenAI after retries")
                return [], similar_faiss_ids
            
            # Parse the response
            response_text = response.choices[0].message.content.strip()
            
            if self.debug:
                print(f"OpenAI response: {response_text}")
            
            # Try to extract JSON from the response
            try:
                # Handle cases where the response might have markdown formatting
                if response_text.startswith('```json'):
                    response_text = response_text.replace('```json', '').replace('```', '').strip()
                elif response_text.startswith('```'):
                    response_text = response_text.replace('```', '').strip()
                
                ticker_sentiments = json.loads(response_text)
                
                # Validate the response format
                if not isinstance(ticker_sentiments, list):
                    if self.debug:
                        print(f"Response is not a list: {type(ticker_sentiments)}")
                    return [], similar_faiss_ids
                
                # Validate and filter the results
                valid_results = []
                for item in ticker_sentiments:
                    if not isinstance(item, dict):
                        continue
                    
                    ticker = item.get('ticker', '').upper()
                    sentiment = item.get('sentiment', '').lower()
                    
                    # Validate ticker format and sentiment
                    if (ticker and 
                        sentiment in ['positive', 'negative', 'neutral'] and
                        len(ticker) <= 5 and 
                        ticker.isalpha()):
                        
                        # Optional: Filter to only known S&P 500 tickers for higher quality
                        if ticker in self.sp500_tickers:
                            valid_results.append({
                                'ticker': ticker,
                                'sentiment': sentiment
                            })
                        elif self.debug:
                            print(f"Ticker {ticker} not in S&P 500 list, skipping")
                
                if self.debug:
                    print(f"Valid results: {valid_results}")
                    print(f"Similar articles used: {len(similar_faiss_ids)} articles with scores")
                    if similar_faiss_ids:
                        print(f"  ID-Score pairs: {similar_faiss_ids}")
                
                return valid_results, similar_faiss_ids
                
            except json.JSONDecodeError as e:
                if self.debug:
                    print(f"JSON decode error: {e}")
                    print(f"Response text: {response_text}")
                return [], similar_faiss_ids
                
        except Exception as e:
            if self.debug:
                print(f"Error in OpenAI analysis: {e}")
            else:
                logger.error(f"Error in OpenAI sentiment analysis: {e}")
            return [], []
    
    def store_sentiment_analysis(self, simulation_id, date, news_item, ticker_sentiments, similar_faiss_ids=None):
        """
        Store multiple sentiment analysis results in the database
        
        Args:
            simulation_id: ID of the current simulation run
            date: Trading date
            news_item: News item from database
            ticker_sentiments: List of dicts with 'ticker' and 'sentiment' keys
            similar_faiss_ids: List of [faiss_id, similarity_score] pairs used for RAG context
        """
        try:
            # First, check if we already have sentiment analysis for this news item in this simulation
            existing_count = self.session.query(NewsSentiment).filter(
                and_(
                    NewsSentiment.simulation_id == simulation_id,
                    NewsSentiment.date == date,
                    NewsSentiment.headline_id == news_item.id
                )
            ).count()
            
            if existing_count > 0:
                if self.debug:
                    print(f"Sentiment analysis already exists for news item {news_item.id} in simulation {simulation_id}")
                return
            
            # Store each ticker/sentiment pair as a separate row
            for ticker_sentiment in ticker_sentiments:
                news_sentiment = NewsSentiment(
                    simulation_id=simulation_id,
                    date=date,
                    headline_id=news_item.id,
                    sentiment=ticker_sentiment['sentiment'],
                    ticker=ticker_sentiment['ticker'],
                    similar_news_faiss_ids=similar_faiss_ids or [],
                    extra_data={'source': 'openai_llm_with_rag'}
                )
                self.session.add(news_sentiment)
            
            if ticker_sentiments:
                self.session.commit()
                if self.debug:
                    print(f"Stored {len(ticker_sentiments)} sentiment analyses for news item {news_item.id}")
            
        except Exception as e:
            print(f"Error storing sentiment analysis: {e}")
            self.session.rollback()
    
    def get_trading_signals(self, date, simulation_id):
        """
        Get trading signals for a specific date based on news sentiment
        
        Args:
            date: datetime.date object
            simulation_id: ID of the current simulation run
            
        Returns:
            dict with 'long' and 'short' lists of tickers
        """
        # Calculate previous trading day
        prev_date = date - timedelta(days=1)
        
        # Skip weekends
        while prev_date.weekday() > 4:  # 5 = Saturday, 6 = Sunday
            prev_date = prev_date - timedelta(days=1)
        
        # Query news from database for the relevant time range
        # From previous day 4PM to current day 9:30AM (market open)
        start_time = datetime.combine(prev_date, datetime.min.time()).replace(hour=16, minute=0)
        end_time = datetime.combine(date, datetime.min.time()).replace(hour=9, minute=30)
        
        # Query news from database
        relevant_news = self.session.query(News).filter(
            and_(
                News.time_published >= start_time,
                News.time_published <= end_time
            )
        ).order_by(News.time_published).all()
        
        print(f"Found {len(relevant_news)} news articles for {date} from database")
        
        # Analyze sentiment for each article and store in database
        ticker_sentiment_counts = defaultdict(lambda: {'positive': 0, 'negative': 0, 'neutral': 0})
        
        if self.debug:
            processed_articles = 0
            total_ticker_sentiment_pairs = 0
        
        for news_item in relevant_news:
            # Use LLM to analyze sentiment and extract tickers
            ticker_sentiments, similar_faiss_ids = self.analyze_news_sentiment(news_item.title, news_item.summary)
            
            if ticker_sentiments:
                # Store in database with simulation_id and similar article IDs
                self.store_sentiment_analysis(simulation_id, date, news_item, ticker_sentiments, similar_faiss_ids)
                
                # Count sentiments by ticker
                for ticker_sentiment in ticker_sentiments:
                    ticker = ticker_sentiment['ticker']
                    sentiment = ticker_sentiment['sentiment']
                    ticker_sentiment_counts[ticker][sentiment] += 1
                
                if self.debug:
                    processed_articles += 1
                    total_ticker_sentiment_pairs += len(ticker_sentiments)
                    tickers_found = [ts['ticker'] for ts in ticker_sentiments]
                    sentiments_found = [ts['sentiment'] for ts in ticker_sentiments]
                    print(f"  {news_item.title[:80]}... -> {list(zip(tickers_found, sentiments_found))}")
        
        if self.debug:
            print(f"\nProcessed {processed_articles} articles with {total_ticker_sentiment_pairs} ticker-sentiment pairs")
            print(f"Unique tickers found: {len(ticker_sentiment_counts)}")
        
        # Calculate net sentiment (positive - negative) for each ticker
        ticker_net_sentiment = {}
        for ticker, counts in ticker_sentiment_counts.items():
            net_sentiment = counts['positive'] - counts['negative']
            ticker_net_sentiment[ticker] = net_sentiment
        
        if self.debug:
            print(f"\nTicker net sentiment (positive - negative):")
            for ticker, net_sentiment in sorted(ticker_net_sentiment.items(), key=lambda x: x[1], reverse=True)[:10]:
                counts = ticker_sentiment_counts[ticker]
                total_articles = counts['positive'] + counts['negative'] + counts['neutral']
                print(f"  {ticker}: {net_sentiment:+d} (pos:{counts['positive']}, neg:{counts['negative']}, neu:{counts['neutral']}, total:{total_articles})")
        
        # Sort tickers by net sentiment (positive - negative)
        sorted_tickers = sorted(ticker_net_sentiment.items(), key=lambda x: x[1], reverse=True)
        
        # Get top 5 for long (highest positive-negative) and bottom 5 for short (lowest positive-negative)
        long_tickers = []
        short_tickers = []
        
        # Get tickers with highest net positive sentiment for long positions
        for ticker, net_sentiment in sorted_tickers:
            if net_sentiment > 0 and len(long_tickers) < 5:
                long_tickers.append(ticker)
        
        # Get tickers with lowest net sentiment (most negative) for short positions
        for ticker, net_sentiment in reversed(sorted_tickers):
            if net_sentiment < 0 and len(short_tickers) < 5:
                short_tickers.append(ticker)
        
        # Ensure equal number of long and short positions
        min_positions = min(len(long_tickers), len(short_tickers))
        long_tickers = long_tickers[:min_positions]
        short_tickers = short_tickers[:min_positions]
        
        print(f"Trading signals for {date}:")
        print(f"  Long: {long_tickers}")
        print(f"  Short: {short_tickers}")
        
        return {
            'long': long_tickers,
            'short': short_tickers
        }
    
    def close(self):
        """Clean up resources"""
        if self.session:
            self.session.close() 