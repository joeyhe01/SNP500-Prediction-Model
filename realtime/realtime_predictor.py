#!/usr/bin/env python3
"""
Realtime Trading Predictor
Uses aggregated news and sentiment analysis to generate real-time trading predictions
"""

import json
import logging
import threading
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set tokenizers parallelism to avoid multiprocessing issues
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from realtime.news_aggregator import RealtimeNewsAggregator
from models.llm_sentiment_model import LLMSentimentModel
from models.database import get_db_session, News, RealtimePrediction, NewsSentiment
from sqlalchemy import and_, func

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealtimeTradingPredictor:
    def __init__(self, debug=False, database_only=False, max_workers=4):
        """Initialize the realtime predictor"""
        self.news_aggregator = RealtimeNewsAggregator()
        self.sentiment_model = LLMSentimentModel(debug=debug)
        self.db_session = get_db_session()
        self.debug = debug
        self.database_only = database_only
        # Reduce max workers to prevent resource exhaustion
        self.max_workers = min(max_workers, 4)  # Cap at 4 to prevent issues
        self.analysis_lock = threading.Lock()  # For thread-safe database operations
        
    def cleanup(self):
        """Clean up resources to prevent leaks"""
        try:
            if hasattr(self, 'db_session') and self.db_session:
                self.db_session.close()
            if hasattr(self, 'news_aggregator'):
                self.news_aggregator.close()
            if hasattr(self, 'sentiment_model') and hasattr(self.sentiment_model, 'session'):
                self.sentiment_model.session.close()
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()
        
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
    
    def _analyze_single_article(self, article: Dict, prediction_id: int = None) -> List[Dict]:
        """Analyze sentiment for a single article (thread worker function)"""
        try:
            # Use LLM to analyze sentiment and extract multiple tickers
            ticker_sentiments, similar_faiss_ids = self.sentiment_model.analyze_news_sentiment(
                article['title'], 
                article.get('summary')
            )
            
            analyzed_articles = []
            if ticker_sentiments:
                # Create an analyzed article for each ticker/sentiment pair
                for ticker_sentiment in ticker_sentiments:
                    analyzed_article = {
                        **article,
                        'ticker': ticker_sentiment['ticker'],
                        'sentiment': ticker_sentiment['sentiment'],
                        'similar_faiss_ids': similar_faiss_ids,
                        'analyzed_at': datetime.now()
                    }
                    analyzed_articles.append(analyzed_article)
                
                # Store sentiment analysis in database if prediction_id is provided
                # Use lock to ensure thread-safe database operations
                if prediction_id is not None:
                    with self.analysis_lock:
                        self.store_sentiment_analysis(prediction_id, article, ticker_sentiments, similar_faiss_ids)
                
                if self.debug:
                    tickers_found = [ts['ticker'] for ts in ticker_sentiments]
                    sentiments_found = [ts['sentiment'] for ts in ticker_sentiments]
                    logger.info(f"  {article['title'][:80]}... -> {list(zip(tickers_found, sentiments_found))}")
            
            return analyzed_articles
            
        except Exception as e:
            logger.error(f"Error analyzing article '{article.get('title', 'Unknown')[:50]}...': {e}")
            return []
    
    def analyze_news_sentiment(self, news_articles: List[Dict], prediction_id: int = None) -> List[Dict]:
        """Analyze sentiment for each news article and extract tickers using LLM with multi-threading"""
        analyzed_articles = []
        
        logger.info(f"Analyzing sentiment for {len(news_articles)} articles using {self.max_workers} threads...")
        
        start_time = time.time()
        
        # Use ThreadPoolExecutor to process articles in parallel
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="sentiment_") as executor:
                # Submit all articles for processing
                future_to_article = {
                    executor.submit(self._analyze_single_article, article, prediction_id): article 
                    for article in news_articles
                }
                
                # Collect results as they complete
                completed_count = 0
                for future in as_completed(future_to_article):
                    try:
                        article_results = future.result(timeout=60)  # Add timeout
                        analyzed_articles.extend(article_results)
                        completed_count += 1
                        
                        # Log progress every 50 articles to reduce log spam
                        if completed_count % 50 == 0 or completed_count > len(news_articles) - 5:
                            logger.info(f"Progress: {completed_count}/{len(news_articles)} articles processed")
                    except Exception as e:
                        completed_count += 1
                        logger.error(f"Error processing article: {e}")
                        continue
        except Exception as e:
            logger.error(f"ThreadPoolExecutor error: {e}")
            # Fallback to sequential processing if threading fails
            logger.info("Falling back to sequential processing...")
            for article in news_articles:
                try:
                    results = self._analyze_single_article(article, prediction_id)
                    analyzed_articles.extend(results)
                except Exception as e:
                    logger.error(f"Error in sequential processing: {e}")
                    continue
                        
                except Exception as e:
                    article = future_to_article[future]
                    logger.error(f"Error processing article '{article.get('title', 'Unknown')[:50]}...': {e}")
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        logger.info(f"Successfully analyzed {len(analyzed_articles)} ticker-article pairs from {len(news_articles)} articles")
        logger.info(f"Processing time: {processing_time:.2f} seconds ({processing_time/len(news_articles):.2f}s per article)")
        logger.info(f"Effective rate: {len(news_articles) * 60 / processing_time:.1f} articles per minute")
        
        return analyzed_articles
    
    def store_sentiment_analysis(self, prediction_id: int, article: Dict, ticker_sentiments: List[Dict], similar_faiss_ids: List = None):
        """Store multiple sentiment analysis results in database for realtime predictions"""
        try:
            # Use negative prediction_id to distinguish realtime predictions from simulations
            # This allows us to reuse the same NewsSentiment table
            simulation_id = -prediction_id
            
            # Use the article's published date
            article_date = article['time_published'].date()
            
            # Check if we already have sentiment analysis for this article in this prediction
            existing_count = self.db_session.query(NewsSentiment).filter(
                and_(
                    NewsSentiment.simulation_id == simulation_id,
                    NewsSentiment.headline_id == article['id'],
                    NewsSentiment.date == article_date
                )
            ).count()
            
            if existing_count == 0:
                # Store each ticker/sentiment pair as a separate row
                for ticker_sentiment in ticker_sentiments:
                    news_sentiment = NewsSentiment(
                        simulation_id=simulation_id,
                        date=article_date,
                        headline_id=article['id'],
                        sentiment=ticker_sentiment['sentiment'],
                        ticker=ticker_sentiment['ticker'],
                        similar_news_faiss_ids=similar_faiss_ids,  # Store similar_faiss_ids
                        extra_data={'realtime_prediction_id': prediction_id, 'source': 'openai_llm'}
                    )
                    self.db_session.add(news_sentiment)
                
                if ticker_sentiments:
                    self.db_session.commit()
                    
                    if self.debug:
                        tickers_sentiments = [(ts['ticker'], ts['sentiment']) for ts in ticker_sentiments]
                        logger.info(f"Stored {len(ticker_sentiments)} sentiment analyses for article {article['id']}: {tickers_sentiments}")
                        
        except Exception as e:
            logger.error(f"Error storing sentiment analysis: {e}")
            self.db_session.rollback()

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
            
            # Step 2: Create placeholder prediction to get prediction_id
            placeholder_prediction = RealtimePrediction(
                timestamp=datetime.now(),
                prediction_data={'status': 'processing'},
                long_tickers=[],
                short_tickers=[],
                market_sentiment_score=0.0
            )
            self.db_session.add(placeholder_prediction)
            self.db_session.commit()
            prediction_id = placeholder_prediction.id
            logger.info(f"Created placeholder prediction with ID: {prediction_id}")
            
            # Step 3: Analyze sentiment with prediction_id for storage
            analyzed_articles = self.analyze_news_sentiment(news_articles, prediction_id)
            if not analyzed_articles:
                logger.warning("No articles with ticker mentions found")
                # Clean up placeholder prediction
                self.db_session.delete(placeholder_prediction)
                self.db_session.commit()
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
            
            # Step 4: Generate trading signals
            signals = self.generate_trading_signals(analyzed_articles)
            
            # Add time range information to signals
            signals['time_range_used'] = {
                'start': start_time.isoformat() if start_time else None,
                'end': end_time.isoformat() if end_time else None,
                'is_custom': bool(start_time and end_time)
            }
            
            # Step 5: Update prediction with actual results
            placeholder_prediction.prediction_data = {
                'long_signals': signals['long_signals'],
                'short_signals': signals['short_signals'],
                'market_sentiment': signals['market_sentiment'],
                'total_articles': signals['total_articles_analyzed'],
                'unique_tickers': signals['unique_tickers'],
                'time_range_used': signals.get('time_range_used')
            }
            placeholder_prediction.long_tickers = [s['ticker'] for s in signals['long_signals']]
            placeholder_prediction.short_tickers = [s['ticker'] for s in signals['short_signals']]
            placeholder_prediction.market_sentiment_score = signals['market_sentiment']
            placeholder_prediction.timestamp = signals['timestamp']
            self.db_session.commit()
            logger.info(f"Updated prediction {prediction_id} with final results")
            
            # Step 6: Prepare response
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
    # Test the realtime predictor with multi-threading
    predictor = RealtimeTradingPredictor(
        debug=True, 
        max_workers=8  # Adjust based on your needs
    )
    try:
        logger.info("Starting realtime prediction with multi-threading...")
        result = predictor.run_realtime_prediction()
        print(json.dumps(result, indent=2, default=str))
    finally:
        predictor.close() 