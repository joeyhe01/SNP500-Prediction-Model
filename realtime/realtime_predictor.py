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
        
    def get_realtime_news(self, start_time=None, end_time=None) -> List[Dict]:
        """Get the latest news for analysis"""
        if self.database_only:
            logger.info("Fetching news from database only (no API calls)...")
        else:
            logger.info("Fetching realtime news...")
        
        # If database_only mode, skip API calls entirely
        if not self.database_only:
            # First, try to get fresh news from APIs
            try:
                if start_time and end_time:
                    news_articles = self.news_aggregator.aggregate_all_news_custom_range(start_time, end_time)
                else:
                    news_articles = self.news_aggregator.run_realtime_aggregation()
                if news_articles:
                    logger.info(f"Got {news_articles} fresh articles from APIs")
                    # For API mode, we need to fetch the news from database after saving
                    # to get it in the expected format
                    pass  # Continue to database fetch below
            except Exception as e:
                logger.error(f"Error fetching fresh news: {e}")
        
        # Get news from database (fallback for API mode, primary for database_only mode)
        if start_time and end_time:
            logger.info(f"Using custom time range (UTC): {start_time} to {end_time}")
            logger.info(f"Custom time range (Local): {start_time.astimezone()} to {end_time.astimezone()}")
        else:
            start_time, end_time = self.news_aggregator.get_time_range()
            logger.info(f"Using default time range (UTC): {start_time} to {end_time}")
            logger.info(f"Default time range (Local): {start_time.astimezone()} to {end_time.astimezone()}")
        
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
        
        # Count sentiment types by ticker
        ticker_sentiment_counts = defaultdict(lambda: {'positive': 0, 'negative': 0, 'neutral': 0})
        ticker_articles = defaultdict(list)
        
        for article in analyzed_articles:
            ticker = article['ticker']
            sentiment = article['sentiment']
            
            # Count sentiments by type
            ticker_sentiment_counts[ticker][sentiment] += 1
            ticker_articles[ticker].append(article)
        
        # Calculate net sentiment (positive - negative) for each ticker
        ticker_net_scores = {}
        for ticker, counts in ticker_sentiment_counts.items():
            net_sentiment = counts['positive'] - counts['negative']
            total_articles = counts['positive'] + counts['negative'] + counts['neutral']
            
            ticker_net_scores[ticker] = {
                'net_sentiment': net_sentiment,
                'positive_count': counts['positive'],
                'negative_count': counts['negative'],
                'neutral_count': counts['neutral'],
                'total_articles': total_articles,
                'articles': ticker_articles[ticker]
            }
        
        # Sort tickers by net sentiment (positive - negative)
        sorted_tickers = sorted(ticker_net_scores.items(), key=lambda x: x[1]['net_sentiment'], reverse=True)
        
        # Get trading signals
        long_signals = []
        short_signals = []
        
        # Get tickers with highest net positive sentiment for long positions
        for ticker, data in sorted_tickers:
            if data['net_sentiment'] > 0 and len(long_signals) < 5:
                long_signals.append({
                    'ticker': ticker,
                    'net_sentiment': data['net_sentiment'],
                    'positive_count': data['positive_count'],
                    'negative_count': data['negative_count'],
                    'total_articles': data['total_articles'],
                    'signal_strength': abs(data['net_sentiment']),
                    'position_type': 'long'
                })
        
        # Get tickers with lowest net sentiment (most negative) for short positions
        for ticker, data in reversed(sorted_tickers):
            if data['net_sentiment'] < 0 and len(short_signals) < 5:
                short_signals.append({
                    'ticker': ticker,
                    'net_sentiment': data['net_sentiment'],
                    'positive_count': data['positive_count'],
                    'negative_count': data['negative_count'],
                    'total_articles': data['total_articles'],
                    'signal_strength': abs(data['net_sentiment']),
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
            'unique_tickers': len(ticker_net_scores),
            'market_sentiment': self._calculate_market_sentiment(ticker_net_scores)
        }
        
        if self.debug:
            logger.info("Trading Signals Generated:")
            logger.info("  Long positions:")
            for signal in long_signals:
                logger.info(f"    {signal['ticker']}: net={signal['net_sentiment']:+d} (pos:{signal['positive_count']}, neg:{signal['negative_count']}, total:{signal['total_articles']})")
            logger.info("  Short positions:")
            for signal in short_signals:
                logger.info(f"    {signal['ticker']}: net={signal['net_sentiment']:+d} (pos:{signal['positive_count']}, neg:{signal['negative_count']}, total:{signal['total_articles']})")
            logger.info(f"  Market sentiment: {signals['market_sentiment']:.2f}")
        
        return signals
    
    def _calculate_market_sentiment(self, ticker_net_scores: Dict) -> float:
        """Calculate overall market sentiment based on net sentiment scores"""
        if not ticker_net_scores:
            return 0.0
        
        # Calculate weighted average based on total article counts
        total_weighted_sentiment = 0
        total_articles = 0
        
        for data in ticker_net_scores.values():
            net_sentiment = data['net_sentiment']
            article_count = data['total_articles']
            
            total_weighted_sentiment += net_sentiment * article_count
            total_articles += article_count
        
        if total_articles == 0:
            return 0.0
            
        return total_weighted_sentiment / total_articles
    
    def store_prediction(self, signals: Dict):
        """Store the prediction in the database"""
        try:
            prediction_data = {
                'long_signals': signals['long_signals'],
                'short_signals': signals['short_signals'],
                'market_sentiment': signals['market_sentiment'],
                'total_articles': signals['total_articles_analyzed'],
                'unique_tickers': signals['unique_tickers'],
                'time_range_used': signals.get('time_range_used')  # Store the time range information
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
        return self._run_prediction_pipeline()
    
    def run_realtime_prediction_custom_range(self, start_time: datetime, end_time: datetime) -> Dict:
        """Run realtime prediction pipeline with custom time range"""
        return self._run_prediction_pipeline(start_time, end_time)
    
    def _run_prediction_pipeline(self, start_time=None, end_time=None) -> Dict:
        """Internal method to run the realtime prediction pipeline"""
        if start_time and end_time:
            logger.info(f"=== Starting Realtime Prediction Pipeline (Custom Range) ===")
            logger.info(f"Custom Range (UTC): {start_time} to {end_time}")
            logger.info(f"Custom Range (Local): {start_time.astimezone()} to {end_time.astimezone()}")
        else:
            logger.info("=== Starting Realtime Prediction Pipeline (Default Range) ===")
        
        try:
            # Step 1: Get latest news
            news_articles = self.get_realtime_news(start_time, end_time)
            if not news_articles:
                logger.warning("No news articles found for analysis")
                return {
                    'success': False,
                    'message': 'No news articles found',
                    'timestamp': datetime.now(),
                    'time_range_used': {
                        'start': start_time.isoformat() if start_time else None,
                        'end': end_time.isoformat() if end_time else None,
                        'is_custom': bool(start_time and end_time)
                    }
                }
            
            # Step 2: Analyze sentiment
            analyzed_articles = self.analyze_news_sentiment(news_articles)
            if not analyzed_articles:
                logger.warning("No articles with ticker mentions found")
                return {
                    'success': False,
                    'message': 'No articles with ticker mentions found',
                    'timestamp': datetime.now(),
                    'time_range_used': {
                        'start': start_time.isoformat() if start_time else None,
                        'end': end_time.isoformat() if end_time else None,
                        'is_custom': bool(start_time and end_time)
                    }
                }
            
            # Step 3: Generate trading signals
            signals = self.generate_trading_signals(analyzed_articles)
            
            # Add time range information to signals
            signals['time_range_used'] = {
                'start': start_time.isoformat() if start_time else None,
                'end': end_time.isoformat() if end_time else None,
                'is_custom': bool(start_time and end_time)
            }
            
            # Step 4: Store prediction
            prediction_id = self.store_prediction(signals)
            
            # Step 5: Prepare response
            result = {
                'success': True,
                'prediction_id': prediction_id,
                'signals': signals,
                'analyzed_articles': len(analyzed_articles),
                'timestamp': signals['timestamp'],
                'time_range_used': signals['time_range_used']
            }
            
            logger.info("=== Realtime Prediction Pipeline Completed Successfully ===")
            return result
            
        except Exception as e:
            logger.error(f"Error in realtime prediction pipeline: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now(),
                'time_range_used': {
                    'start': start_time.isoformat() if start_time else None,
                    'end': end_time.isoformat() if end_time else None,
                    'is_custom': bool(start_time and end_time)
                }
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