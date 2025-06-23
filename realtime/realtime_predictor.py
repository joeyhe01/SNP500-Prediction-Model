#!/usr/bin/env python3
"""
Realtime Trading Predictor
Uses aggregated news and sentiment analysis to generate real-time trading predictions
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import defaultdict

from realtime.news_aggregator import RealtimeNewsAggregator
from models.base_sentiment_model import BaseSentimentModel
from models.database import get_db_session, News, RealtimePrediction
from sqlalchemy import and_, func

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealtimeTradingPredictor:
    def __init__(self, debug=False, database_only=False):
        """Initialize the realtime predictor"""
        self.news_aggregator = RealtimeNewsAggregator()
        self.sentiment_model = BaseSentimentModel(debug=debug)
        self.db_session = get_db_session()
        self.debug = debug
        self.database_only = database_only
        
    def get_realtime_news(self) -> List[Dict]:
        """Get the latest news for analysis"""
        if self.database_only:
            logger.info("Fetching news from database only (no API calls)...")
        else:
            logger.info("Fetching realtime news...")
        
        # If database_only mode, skip API calls entirely
        if not self.database_only:
            # First, try to get fresh news from APIs
            try:
                news_articles = self.news_aggregator.run_realtime_aggregation()
                if news_articles:
                    logger.info(f"Got {len(news_articles)} fresh articles from APIs")
                    return news_articles
            except Exception as e:
                logger.error(f"Error fetching fresh news: {e}")
        
        # Get news from database (fallback for API mode, primary for database_only mode)
        start_time, end_time = self.news_aggregator.get_time_range()
        
        db_news = self.db_session.query(News).filter(
            and_(
                News.time_published >= start_time,
                News.time_published <= end_time
            )
        ).order_by(News.time_published.desc()).all()
        
        # Convert to the expected format
        news_articles = []
        for news_item in db_news:
            news_articles.append({
                'id': news_item.id,
                'title': news_item.title,
                'summary': news_item.summary,
                'source': news_item.source,
                'url': news_item.url,
                'time_published': news_item.time_published,
                'api_source': 'database'
            })
        
        if self.database_only:
            logger.info(f"Got {len(news_articles)} articles from database (database-only mode)")
        else:
            logger.info(f"Got {len(news_articles)} articles from database (API fallback)")
        return news_articles
    
    def analyze_news_sentiment(self, news_articles: List[Dict]) -> List[Dict]:
        """Analyze sentiment for each news article and extract tickers"""
        analyzed_articles = []
        
        logger.info(f"Analyzing sentiment for {len(news_articles)} articles...")
        
        for article in news_articles:
            try:
                # Extract ticker from headline
                ticker = self.sentiment_model.extract_ticker_from_headline(article['title'])
                
                if ticker:
                    # Analyze sentiment
                    sentiment = self.sentiment_model.analyze_headline_sentiment(
                        article['title'], ticker
                    )
                    
                    analyzed_article = {
                        **article,
                        'ticker': ticker,
                        'sentiment': sentiment,
                        'analyzed_at': datetime.now()
                    }
                    analyzed_articles.append(analyzed_article)
                    
                    if self.debug:
                        logger.info(f"  {article['title'][:80]}... -> {ticker} ({sentiment})")
                        
            except Exception as e:
                logger.error(f"Error analyzing article: {e}")
                continue
        
        logger.info(f"Successfully analyzed {len(analyzed_articles)} articles with ticker mentions")
        return analyzed_articles
    
    def generate_trading_signals(self, analyzed_articles: List[Dict]) -> Dict:
        """Generate trading signals based on sentiment analysis"""
        logger.info("Generating trading signals...")
        
        # Aggregate sentiment scores by ticker
        ticker_sentiments = defaultdict(list)
        ticker_articles = defaultdict(list)
        
        for article in analyzed_articles:
            ticker = article['ticker']
            sentiment = article['sentiment']
            
            # Convert sentiment to score
            if sentiment == 'positive':
                score = 1
            elif sentiment == 'negative':
                score = -1
            else:
                score = 0
            
            ticker_sentiments[ticker].append(score)
            ticker_articles[ticker].append(article)
        
        # Calculate average sentiment scores
        ticker_scores = {}
        for ticker, sentiments in ticker_sentiments.items():
            ticker_scores[ticker] = {
                'score': sum(sentiments) / len(sentiments),
                'article_count': len(sentiments),
                'articles': ticker_articles[ticker]
            }
        
        # Sort tickers by sentiment score
        sorted_tickers = sorted(ticker_scores.items(), key=lambda x: x[1]['score'], reverse=True)
        
        # Get trading signals
        long_signals = []
        short_signals = []
        
        # Get top positive sentiment stocks for long positions
        for ticker, data in sorted_tickers:
            if data['score'] > 0 and len(long_signals) < 5:
                long_signals.append({
                    'ticker': ticker,
                    'score': data['score'],
                    'article_count': data['article_count'],
                    'signal_strength': abs(data['score']),
                    'position_type': 'long'
                })
        
        # Get top negative sentiment stocks for short positions
        for ticker, data in reversed(sorted_tickers):
            if data['score'] < 0 and len(short_signals) < 5:
                short_signals.append({
                    'ticker': ticker,
                    'score': data['score'],
                    'article_count': data['article_count'],
                    'signal_strength': abs(data['score']),
                    'position_type': 'short'
                })
        
        # Balance positions (equal number of long and short)
        min_positions = min(len(long_signals), len(short_signals))
        long_signals = long_signals[:min_positions]
        short_signals = short_signals[:min_positions]
        
        signals = {
            'timestamp': datetime.now(),
            'long_signals': long_signals,
            'short_signals': short_signals,
            'total_articles_analyzed': len(analyzed_articles),
            'unique_tickers': len(ticker_scores),
            'market_sentiment': self._calculate_market_sentiment(ticker_scores)
        }
        
        if self.debug:
            logger.info("Trading Signals Generated:")
            logger.info(f"  Long positions: {[s['ticker'] for s in long_signals]}")
            logger.info(f"  Short positions: {[s['ticker'] for s in short_signals]}")
            logger.info(f"  Market sentiment: {signals['market_sentiment']:.2f}")
        
        return signals
    
    def _calculate_market_sentiment(self, ticker_scores: Dict) -> float:
        """Calculate overall market sentiment"""
        if not ticker_scores:
            return 0.0
        
        all_scores = [data['score'] for data in ticker_scores.values()]
        return sum(all_scores) / len(all_scores)
    
    def store_prediction(self, signals: Dict):
        """Store the prediction in the database"""
        try:
            prediction_data = {
                'long_signals': signals['long_signals'],
                'short_signals': signals['short_signals'],
                'market_sentiment': signals['market_sentiment'],
                'total_articles': signals['total_articles_analyzed'],
                'unique_tickers': signals['unique_tickers']
            }
            
            prediction = RealtimePrediction(
                timestamp=signals['timestamp'],
                prediction_data=prediction_data,
                long_tickers=[s['ticker'] for s in signals['long_signals']],
                short_tickers=[s['ticker'] for s in signals['short_signals']],
                market_sentiment_score=signals['market_sentiment']
            )
            
            self.db_session.add(prediction)
            self.db_session.commit()
            
            logger.info(f"Stored prediction with ID: {prediction.id}")
            return prediction.id
            
        except Exception as e:
            logger.error(f"Error storing prediction: {e}")
            self.db_session.rollback()
            return None
    
    def run_realtime_prediction(self) -> Dict:
        """Main method to run the realtime prediction pipeline"""
        logger.info("=== Starting Realtime Prediction Pipeline ===")
        
        try:
            # Step 1: Get latest news
            news_articles = self.get_realtime_news()
            if not news_articles:
                logger.warning("No news articles found for analysis")
                return {
                    'success': False,
                    'message': 'No news articles found',
                    'timestamp': datetime.now()
                }
            
            # Step 2: Analyze sentiment
            analyzed_articles = self.analyze_news_sentiment(news_articles)
            if not analyzed_articles:
                logger.warning("No articles with ticker mentions found")
                return {
                    'success': False,
                    'message': 'No articles with ticker mentions found',
                    'timestamp': datetime.now()
                }
            
            # Step 3: Generate trading signals
            signals = self.generate_trading_signals(analyzed_articles)
            
            # Step 4: Store prediction
            prediction_id = self.store_prediction(signals)
            
            # Step 5: Prepare response
            result = {
                'success': True,
                'prediction_id': prediction_id,
                'signals': signals,
                'analyzed_articles': len(analyzed_articles),
                'timestamp': signals['timestamp']
            }
            
            logger.info("=== Realtime Prediction Pipeline Completed Successfully ===")
            return result
            
        except Exception as e:
            logger.error(f"Error in realtime prediction pipeline: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now()
            }
    
    def get_latest_prediction(self) -> Dict:
        """Get the most recent prediction from database"""
        try:
            latest_prediction = self.db_session.query(RealtimePrediction)\
                .order_by(RealtimePrediction.timestamp.desc())\
                .first()
            
            if not latest_prediction:
                return None
            
            return {
                'id': latest_prediction.id,
                'timestamp': latest_prediction.timestamp,
                'prediction_data': latest_prediction.prediction_data,
                'long_tickers': latest_prediction.long_tickers,
                'short_tickers': latest_prediction.short_tickers,
                'market_sentiment_score': latest_prediction.market_sentiment_score
            }
            
        except Exception as e:
            logger.error(f"Error getting latest prediction: {e}")
            return None
    
    def close(self):
        """Clean up resources"""
        self.news_aggregator.close()
        self.sentiment_model.close()
        self.db_session.close()

if __name__ == "__main__":
    # Test the realtime predictor
    predictor = RealtimeTradingPredictor(debug=True)
    try:
        result = predictor.run_realtime_prediction()
        print(json.dumps(result, indent=2, default=str))
    finally:
        predictor.close() 