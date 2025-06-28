#!/usr/bin/env python3
"""
Flask web application for S&P 500 trading simulation analysis
"""

from flask import Flask, jsonify, request, send_from_directory, send_file
from models.database import get_db_session
from models.database import Simulation, DailyRecap, NewsSentiment, News, RealtimePrediction
from sqlalchemy import desc, asc, func, cast, Date, and_
from datetime import datetime, timedelta
import json
import os
import logging
from sqlalchemy.orm import aliased

# Configure logging
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='frontend/build/static', template_folder='frontend/build')

# Serve React App
@app.route('/')
def serve():
    """Serve the React app"""
    return send_from_directory(app.template_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files and handle React routing"""
    if path.startswith('api/'):
        # API routes should not be handled here
        return jsonify({'error': 'API endpoint not found'}), 404
    
    # Try to serve static files first
    try:
        return send_from_directory(app.static_folder, path)
    except:
        # If file not found, serve the React app (for client-side routing)
        return send_from_directory(app.template_folder, 'index.html')

@app.route('/api/simulations')
def get_simulations():
    """Get all simulations with their performance data"""
    session = get_db_session()
    
    try:
        # Get all simulations with their daily performance
        simulations = session.query(Simulation).order_by(desc(Simulation.executed_at)).all()
        
        result = []
        for sim in simulations:
            # Get daily recap data for this simulation
            daily_data = session.query(DailyRecap).filter_by(simulation_id=sim.id).order_by(asc(DailyRecap.date)).all()
            
            if daily_data:
                # Calculate daily returns
                daily_returns = []
                dates = []
                
                for day in daily_data:
                    dates.append(day.date.strftime('%Y-%m-%d'))
                    # Calculate return percentage from starting money
                    if day.starting_money > 0:
                        daily_return = ((day.ending_money - day.starting_money) / day.starting_money) * 100
                    else:
                        daily_return = 0
                    daily_returns.append(round(daily_return, 2))
                
                # Calculate cumulative returns
                cumulative_returns = []
                initial_value = daily_data[0].starting_money
                for day in daily_data:
                    cumulative_return = ((day.ending_money - initial_value) / initial_value) * 100
                    cumulative_returns.append(round(cumulative_return, 2))
                
                # Get simulation metadata
                extra_data = sim.extra_data or {}
                metrics = extra_data.get('metrics', {})
                
                sim_data = {
                    'id': sim.id,
                    'executed_at': sim.executed_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'dates': dates,
                    'daily_returns': daily_returns,
                    'cumulative_returns': cumulative_returns,
                    'final_return': cumulative_returns[-1] if cumulative_returns else 0,
                    'total_trades': extra_data.get('total_trades', 0),
                    'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                    'max_drawdown': metrics.get('max_drawdown_pct', 0),
                    'win_rate': metrics.get('win_rate_pct', 0)
                }
                
                result.append(sim_data)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

@app.route('/api/simulation/<int:simulation_id>')
def get_simulation_details(simulation_id):
    """Get detailed daily data for a specific simulation"""
    session = get_db_session()
    
    try:
        # Get simulation info
        simulation = session.query(Simulation).filter_by(id=simulation_id).first()
        if not simulation:
            return jsonify({'error': 'Simulation not found'}), 404
        
        # Get daily recap data
        daily_data = session.query(DailyRecap).filter_by(simulation_id=simulation_id).order_by(asc(DailyRecap.date)).all()
        
        result = {
            'simulation': {
                'id': simulation.id,
                'executed_at': simulation.executed_at.strftime('%Y-%m-%d %H:%M:%S'),
                'extra_data': simulation.extra_data or {}
            },
            'daily_data': []
        }
        
        for day in daily_data:
            extra_data = day.extra_data or {}
            
            # Parse trading data from extra_data
            trades = extra_data.get('trades', [])
            positions = extra_data.get('positions', [])
            
            # Count net positions at end of day, not individual trades
            num_long_positions = len([p for p in positions if p.get('position_type') == 'long'])
            num_short_positions = len([p for p in positions if p.get('position_type') == 'short'])
            
            day_data = {
                'date': day.date.strftime('%Y-%m-%d'),
                'starting_money': round(day.starting_money, 2),
                'ending_money': round(day.ending_money, 2),
                'daily_pnl': round(day.ending_money - day.starting_money, 2),
                'daily_return': round(((day.ending_money - day.starting_money) / day.starting_money) * 100, 2) if day.starting_money > 0 else 0,
                'trades': trades,
                'positions': positions,
                'num_long_positions': num_long_positions,
                'num_short_positions': num_short_positions,
                'total_trades': len(trades)
            }
            
            result['daily_data'].append(day_data)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

@app.route('/api/simulation/<int:simulation_id>/day/<date>')
def get_day_details(simulation_id, date):
    """Get detailed news and sentiment data for a specific day"""
    session = get_db_session()
    
    try:
        # Parse the date
        try:
            day_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Get all news for this day with optional sentiment analysis
        # Use date() function to extract date part from timestamp
        all_news_query = session.query(News).filter(
            func.date(News.time_published) == day_date
        ).order_by(News.time_published)
        
        all_news = all_news_query.all()
        
        # If no news found, try a broader date range (sometimes timezone issues)
        if not all_news:
            start_datetime = datetime.combine(day_date, datetime.min.time())
            end_datetime = datetime.combine(day_date + timedelta(days=1), datetime.min.time())
            
            all_news_query = session.query(News).filter(
                News.time_published >= start_datetime,
                News.time_published < end_datetime
            ).order_by(News.time_published)
            
            all_news = all_news_query.all()
        
        # Get sentiment data for this simulation and date
        sentiment_data = {}
        sentiment_records = session.query(NewsSentiment).filter(
            NewsSentiment.simulation_id == simulation_id,
            NewsSentiment.date == day_date
        ).all()
        
        # Create a mapping of headline_id to sentiment data
        for sentiment in sentiment_records:
            sentiment_data[sentiment.headline_id] = sentiment
        
        # Get daily recap for context
        daily_recap = session.query(DailyRecap).filter_by(
            simulation_id=simulation_id,
            date=day_date
        ).first()
        
        result = {
            'date': date,
            'simulation_id': simulation_id,
            'daily_summary': None,
            'news_analysis': []
        }
        
        # Add daily summary if available
        if daily_recap:
            extra_data = daily_recap.extra_data or {}
            result['daily_summary'] = {
                'starting_money': round(daily_recap.starting_money, 2),
                'ending_money': round(daily_recap.ending_money, 2),
                'daily_pnl': round(daily_recap.ending_money - daily_recap.starting_money, 2),
                'trades': extra_data.get('trades', []),
                'positions': extra_data.get('positions', {})
            }
        
        # Add all news with sentiment analysis where available
        for news in all_news:
            sentiment = sentiment_data.get(news.id)
            
            news_item = {
                'headline_id': news.id,
                'title': news.title,
                'summary': news.summary,
                'source': news.source,
                'url': news.url,
                'time_published': news.time_published.strftime('%Y-%m-%d %H:%M:%S'),
                'sentiment': sentiment.sentiment if sentiment else None,
                'identified_ticker': sentiment.ticker if sentiment else None,
                'extra_data': sentiment.extra_data if sentiment else None,
                'has_analysis': sentiment is not None
            }
            result['news_analysis'].append(news_item)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

@app.route('/api/simulation/<int:simulation_id>', methods=['DELETE'])
def delete_simulation(simulation_id):
    """Delete a simulation and all its associated data"""
    session = get_db_session()
    
    try:
        # Check if simulation exists
        simulation = session.query(Simulation).filter_by(id=simulation_id).first()
        if not simulation:
            return jsonify({'error': 'Simulation not found'}), 404
        
        # Delete associated data in proper order (foreign key constraints)
        
        # 1. Delete news sentiment records
        news_sentiment_count = session.query(NewsSentiment).filter_by(simulation_id=simulation_id).count()
        session.query(NewsSentiment).filter_by(simulation_id=simulation_id).delete()
        
        # 2. Delete daily recap records  
        daily_recap_count = session.query(DailyRecap).filter_by(simulation_id=simulation_id).count()
        session.query(DailyRecap).filter_by(simulation_id=simulation_id).delete()
        
        # 3. Delete the simulation record itself
        session.delete(simulation)
        
        # Commit all deletions
        session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Simulation {simulation_id} deleted successfully',
            'deleted_records': {
                'news_sentiments': news_sentiment_count,
                'daily_recaps': daily_recap_count,
                'simulation': 1
            }
        })
        
    except Exception as e:
        session.rollback()
        return jsonify({'error': f'Failed to delete simulation: {str(e)}'}), 500
    finally:
        session.close()

# ============== REALTIME TRADING ENDPOINTS ==============

@app.route('/api/realtime/fetch-data', methods=['POST'])
def fetch_realtime_data():
    """Fetch fresh news data from APIs and store in database"""
    try:
        from realtime.news_aggregator import RealtimeNewsAggregator
        
        # Get custom time range from request if provided
        data = request.get_json() or {}
        start_time = None
        end_time = None
        
        if 'start_time' in data and 'end_time' in data:
            try:
                start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
            except ValueError as e:
                return jsonify({
                    'success': False,
                    'error': f'Invalid time format: {str(e)}. Use ISO format.',
                    'timestamp': datetime.now().isoformat()
                }), 400
        
        # Create aggregator instance
        aggregator = RealtimeNewsAggregator()
        
        try:
            # Run the news aggregation with custom time range if provided
            if start_time and end_time:
                news_articles = aggregator.aggregate_all_news_custom_range(start_time, end_time)
                time_range_msg = f" (custom range: {start_time} to {end_time})"
            else:
                news_articles = aggregator.run_realtime_aggregation()
                time_range_msg = " (default range)"
            
            result = {
                'success': True,
                'message': f'Successfully fetched and stored {news_articles} articles{time_range_msg}',
                'articles_fetched': news_articles,
                'timestamp': datetime.now().isoformat(),
                'time_range_used': {
                    'start': start_time.isoformat() if start_time else None,
                    'end': end_time.isoformat() if end_time else None,
                    'is_custom': bool(start_time and end_time)
                }
            }
            
            return jsonify(result)
        finally:
            aggregator.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# Individual news API endpoints
@app.route('/api/realtime/fetch-finnhub', methods=['POST'])
def fetch_finnhub_data():
    """Fetch news data from Finnhub API only"""
    try:
        from realtime.news_aggregator import RealtimeNewsAggregator
        
        # Get custom time range from request if provided
        data = request.get_json() or {}
        start_time = None
        end_time = None
        
        if 'start_time' in data and 'end_time' in data:
            try:
                start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
            except ValueError as e:
                return jsonify({
                    'success': False,
                    'error': f'Invalid time format: {str(e)}. Use ISO format.',
                    'timestamp': datetime.now().isoformat()
                }), 400
        
        # Create aggregator instance
        aggregator = RealtimeNewsAggregator()
        
        try:
            # Use default time range if not provided
            if not start_time or not end_time:
                start_time, end_time = aggregator.get_time_range()
            
            news_articles = aggregator.fetch_finnhub_news_only(start_time, end_time)
            time_range_msg = f" from {start_time} to {end_time}"
            
            result = {
                'success': True,
                'message': f'Successfully fetched and stored {news_articles} articles from Finnhub{time_range_msg}',
                'articles_fetched': news_articles,
                'api_source': 'finnhub',
                'timestamp': datetime.now().isoformat(),
                'time_range_used': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                }
            }
            
            return jsonify(result)
        finally:
            aggregator.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'api_source': 'finnhub',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/realtime/fetch-newsapi-ai', methods=['POST'])
def fetch_newsapi_ai_data():
    """Fetch news data from NewsAPI.ai only"""
    try:
        from realtime.news_aggregator import RealtimeNewsAggregator
        
        # Get custom time range from request if provided
        data = request.get_json() or {}
        start_time = None
        end_time = None
        
        if 'start_time' in data and 'end_time' in data:
            try:
                start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
            except ValueError as e:
                return jsonify({
                    'success': False,
                    'error': f'Invalid time format: {str(e)}. Use ISO format.',
                    'timestamp': datetime.now().isoformat()
                }), 400
        
        # Create aggregator instance
        aggregator = RealtimeNewsAggregator()
        
        try:
            # Use default time range if not provided
            if not start_time or not end_time:
                start_time, end_time = aggregator.get_time_range()
            
            news_articles = aggregator.fetch_newsapi_ai_news_only(start_time, end_time)
            time_range_msg = f" from {start_time} to {end_time}"
            
            result = {
                'success': True,
                'message': f'Successfully fetched and stored {news_articles} articles from NewsAPI.ai{time_range_msg}',
                'articles_fetched': news_articles,
                'api_source': 'newsapi_ai',
                'timestamp': datetime.now().isoformat(),
                'time_range_used': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                }
            }
            
            return jsonify(result)
        finally:
            aggregator.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'api_source': 'newsapi_ai',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/realtime/fetch-alpha-vantage', methods=['POST'])
def fetch_alpha_vantage_data():
    """Fetch news data from Alpha Vantage API only"""
    try:
        from realtime.news_aggregator import RealtimeNewsAggregator
        
        # Get custom time range from request if provided
        data = request.get_json() or {}
        start_time = None
        end_time = None
        
        if 'start_time' in data and 'end_time' in data:
            try:
                start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
            except ValueError as e:
                return jsonify({
                    'success': False,
                    'error': f'Invalid time format: {str(e)}. Use ISO format.',
                    'timestamp': datetime.now().isoformat()
                }), 400
        
        # Create aggregator instance
        aggregator = RealtimeNewsAggregator()
        
        try:
            # Use default time range if not provided
            if not start_time or not end_time:
                start_time, end_time = aggregator.get_time_range()
            
            news_articles = aggregator.fetch_alpha_vantage_news_only(start_time, end_time)
            time_range_msg = f" from {start_time} to {end_time}"
            
            result = {
                'success': True,
                'message': f'Successfully fetched and stored {news_articles} articles from Alpha Vantage{time_range_msg}',
                'articles_fetched': news_articles,
                'api_source': 'alpha_vantage',
                'timestamp': datetime.now().isoformat(),
                'time_range_used': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                }
            }
            
            return jsonify(result)
        finally:
            aggregator.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'api_source': 'alpha_vantage',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/realtime/fetch-newsapi', methods=['POST'])
def fetch_newsapi_data():
    """Fetch news data from NewsAPI.org only"""
    try:
        from realtime.news_aggregator import RealtimeNewsAggregator
        
        # Get custom time range from request if provided
        data = request.get_json() or {}
        start_time = None
        end_time = None
        
        if 'start_time' in data and 'end_time' in data:
            try:
                start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
            except ValueError as e:
                return jsonify({
                    'success': False,
                    'error': f'Invalid time format: {str(e)}. Use ISO format.',
                    'timestamp': datetime.now().isoformat()
                }), 400
        
        # Create aggregator instance
        aggregator = RealtimeNewsAggregator()
        
        try:
            # Use default time range if not provided
            if not start_time or not end_time:
                start_time, end_time = aggregator.get_time_range()
            
            news_articles = aggregator.fetch_newsapi_news_only(start_time, end_time)
            time_range_msg = f" from {start_time} to {end_time}"
            
            result = {
                'success': True,
                'message': f'Successfully fetched and stored {news_articles} articles from NewsAPI.org{time_range_msg}',
                'articles_fetched': news_articles,
                'api_source': 'newsapi_org',
                'timestamp': datetime.now().isoformat(),
                'time_range_used': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                }
            }
            
            return jsonify(result)
        finally:
            aggregator.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'api_source': 'newsapi_org',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/realtime/generate-prediction', methods=['POST'])
def generate_realtime_prediction():
    """Generate a new realtime trading prediction using only database data"""
    try:
        from realtime.realtime_predictor import RealtimeTradingPredictor
        
        # Get custom time range from request if provided
        data = request.get_json() or {}
        start_time = None
        end_time = None
        
        if 'start_time' in data and 'end_time' in data:
            try:
                start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
            except ValueError as e:
                return jsonify({
                    'success': False,
                    'error': f'Invalid time format: {str(e)}. Use ISO format.',
                    'timestamp': datetime.now().isoformat()
                }), 400
        
        # Create predictor instance with database_only mode
        predictor = RealtimeTradingPredictor(debug=False, database_only=True)
        
        try:
            # Run the prediction pipeline with custom time range if provided
            if start_time and end_time:
                result = predictor.run_realtime_prediction_custom_range(start_time, end_time)
            else:
                result = predictor.run_realtime_prediction()
            return jsonify(result)
        finally:
            predictor.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/realtime/latest-prediction')
def get_latest_realtime_prediction():
    """Get the most recent realtime prediction"""
    session = get_db_session()
    
    try:
        # Get the latest prediction
        latest_prediction = session.query(RealtimePrediction)\
            .order_by(desc(RealtimePrediction.timestamp))\
            .first()
        
        if not latest_prediction:
            return jsonify({
                'success': False,
                'message': 'No predictions found',
                'prediction': None
            })
        
        result = {
            'success': True,
            'prediction': {
                'id': latest_prediction.id,
                'timestamp': latest_prediction.timestamp.isoformat(),
                'prediction_data': latest_prediction.prediction_data,
                'long_tickers': latest_prediction.long_tickers,
                'short_tickers': latest_prediction.short_tickers,
                'market_sentiment_score': latest_prediction.market_sentiment_score
            }
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()

@app.route('/api/realtime/predictions')
def get_realtime_predictions():
    """Get recent realtime predictions"""
    session = get_db_session()
    
    try:
        # Get the last 10 predictions
        predictions = session.query(RealtimePrediction)\
            .order_by(desc(RealtimePrediction.timestamp))\
            .limit(10)\
            .all()
        
        result = []
        for pred in predictions:
            result.append({
                'id': pred.id,
                'timestamp': pred.timestamp.isoformat(),
                'prediction_data': pred.prediction_data,
                'long_tickers': pred.long_tickers,
                'short_tickers': pred.short_tickers,
                'market_sentiment_score': pred.market_sentiment_score
            })
        
        return jsonify({
            'success': True,
            'predictions': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()

@app.route('/api/realtime/prediction/<int:prediction_id>')
def get_realtime_prediction_details(prediction_id):
    """Get detailed articles and sentiment data for a specific realtime prediction with pagination"""
    session = get_db_session()
    
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 50, type=int)  # Default 50 articles per page
        max_page_size = 200  # Maximum allowed page size
        
        # Validate pagination parameters
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 50
        if page_size > max_page_size:
            page_size = max_page_size
            
        offset = (page - 1) * page_size
        
        # Get the prediction
        prediction = session.query(RealtimePrediction).filter_by(id=prediction_id).first()
        if not prediction:
            return jsonify({'error': 'Prediction not found'}), 404
        
        # Check if the prediction has stored time range information (from custom range)
        prediction_data = prediction.prediction_data or {}
        stored_time_range = prediction_data.get('time_range_used')
        
        if stored_time_range and stored_time_range.get('start') and stored_time_range.get('end'):
            # Use the stored time range that was actually used for the prediction
            start_time = datetime.fromisoformat(stored_time_range['start'])
            end_time = datetime.fromisoformat(stored_time_range['end'])
            logger.info(f"Using stored time range for prediction {prediction_id}: {start_time} to {end_time}")
        else:
            # Fallback to recalculating based on prediction timestamp (original logic)
            prediction_time = prediction.timestamp
            
            # Use the same time range logic as RealtimeNewsAggregator.get_time_range()
            # But apply it to the prediction timestamp, not current time
            current_time = prediction_time.time()
            
            # If prediction was before 9 AM, get from previous day 5PM to prediction time
            if current_time < datetime.strptime('09:00', '%H:%M').time():
                end_time = prediction_time
                start_time = prediction_time.replace(hour=17, minute=0, second=0, microsecond=0) - timedelta(days=1)
            else:
                # If prediction was after 9 AM, get from previous day 5PM to same day 9AM
                # BUT since we're looking at historical data, we need to be more flexible
                # Let's get from previous day 5PM to the prediction time
                start_time = prediction_time.replace(hour=17, minute=0, second=0, microsecond=0) - timedelta(days=1)
                end_time = prediction_time
                
            # Skip weekends for start_time
            while start_time.weekday() > 4:  # Saturday=5, Sunday=6
                start_time = start_time - timedelta(days=1)
            
            logger.info(f"Recalculated time range for prediction {prediction_id}: {start_time} to {end_time}")
        
        # Get total count of news articles from this time range (for pagination)
        total_articles_query = session.query(News).filter(
            and_(
                News.time_published >= start_time,
                News.time_published <= end_time
            )
        )
        total_articles_count = total_articles_query.count()
        
        # If no articles found in the calculated range, expand to include the full day
        if total_articles_count == 0:
            # Expand to full day of prediction
            day_start = prediction_time.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = prediction_time.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            total_articles_query = session.query(News).filter(
                and_(
                    News.time_published >= day_start,
                    News.time_published <= day_end
                )
            )
            total_articles_count = total_articles_query.count()
            
            # Update the time range for display
            start_time = day_start
            end_time = day_end
        
        # Get paginated news articles
        news_articles = total_articles_query.order_by(News.time_published.desc())\
            .offset(offset)\
            .limit(page_size)\
            .all()
        
        # Calculate pagination metadata
        total_pages = (total_articles_count + page_size - 1) // page_size  # Ceiling division
        has_next = page < total_pages
        has_prev = page > 1
        
        # Now analyze which articles would have been used for this prediction
        # (We'll re-run the sentiment analysis to match what was actually used)
        from models.base_sentiment_model import BaseSentimentModel
        sentiment_model = BaseSentimentModel(debug=False)
        
        analyzed_articles = []
        ticker_mentions = {}
        
        for news_item in news_articles:
            try:
                # Extract ticker from headline (same logic as predictor)
                ticker = sentiment_model.extract_ticker_from_headline(news_item.title)
                
                if ticker:
                    # Analyze sentiment
                    sentiment = sentiment_model.analyze_headline_sentiment(news_item.title, ticker)
                    
                    analyzed_articles.append({
                        'headline_id': news_item.id,
                        'title': news_item.title,
                        'summary': news_item.summary,
                        'source': news_item.source,
                        'url': news_item.url,
                        'time_published': news_item.time_published.strftime('%Y-%m-%d %H:%M:%S'),
                        'sentiment': sentiment,
                        'identified_ticker': ticker,
                        'has_analysis': True,
                        'used_for_prediction': True
                    })
                    
                    # Track ticker mentions for summary
                    if ticker not in ticker_mentions:
                        ticker_mentions[ticker] = {'positive': 0, 'negative': 0, 'neutral': 0}
                    ticker_mentions[ticker][sentiment] += 1
                else:
                    # Include articles without ticker mentions too
                    analyzed_articles.append({
                        'headline_id': news_item.id,
                        'title': news_item.title,
                        'summary': news_item.summary,
                        'source': news_item.source,
                        'url': news_item.url,
                        'time_published': news_item.time_published.strftime('%Y-%m-%d %H:%M:%S'),
                        'sentiment': None,
                        'identified_ticker': None,
                        'has_analysis': False,
                        'used_for_prediction': False
                    })
                    
            except Exception as e:
                print(f"Error analyzing article {news_item.id}: {e}")
                continue
        
        sentiment_model.close()
        
        result = {
            'prediction_id': prediction_id,
            'timestamp': prediction.timestamp.isoformat(),
            'prediction_data': prediction.prediction_data,
            'long_tickers': prediction.long_tickers,
            'short_tickers': prediction.short_tickers,
            'market_sentiment_score': prediction.market_sentiment_score,
            'time_range': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            },
            'time_range_info': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'is_custom': bool(stored_time_range and stored_time_range.get('is_custom', False)),
                'source': 'stored_custom_range' if stored_time_range else 'recalculated_default'
            },
            'articles_analyzed': len([a for a in analyzed_articles if a['has_analysis']]),
            'total_articles': total_articles_count,
            'current_page_articles': len(analyzed_articles),
            'ticker_summary': ticker_mentions,
            'news_analysis': analyzed_articles,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_articles': total_articles_count,
                'total_pages': total_pages,
                'has_next': has_next,
                'has_prev': has_prev,
                'next_page': page + 1 if has_next else None,
                'prev_page': page - 1 if has_prev else None
            }
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

@app.route('/api/realtime/prediction-status')
def get_realtime_prediction_status():
    """Get status information about realtime predictions"""
    session = get_db_session()
    
    try:
        # Get latest prediction timestamp
        latest_prediction = session.query(RealtimePrediction)\
            .order_by(desc(RealtimePrediction.timestamp))\
            .first()
        
        # Count total predictions today
        today = datetime.now().date()
        predictions_today = session.query(RealtimePrediction)\
            .filter(func.date(RealtimePrediction.timestamp) == today)\
            .count()
        
        # Count total predictions
        total_predictions = session.query(RealtimePrediction).count()
        
        result = {
            'success': True,
            'status': {
                'latest_prediction_time': latest_prediction.timestamp.isoformat() if latest_prediction else None,
                'predictions_today': predictions_today,
                'total_predictions': total_predictions,
                'system_time': datetime.now().isoformat()
            }
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()

@app.route('/api/realtime/data-status')
def get_realtime_data_status():
    """Get status information about the news data in database"""
    session = get_db_session()
    
    try:
        # Get latest news article timestamp
        latest_news = session.query(News)\
            .order_by(desc(News.time_published))\
            .first()
        
        # Count news articles today
        today = datetime.now().date()
        news_today = session.query(News)\
            .filter(func.date(News.time_published) == today)\
            .count()
        
        # Count total news articles
        total_news = session.query(News).count()
        
        # Get time range that would be used for prediction
        from realtime.news_aggregator import RealtimeNewsAggregator
        aggregator = RealtimeNewsAggregator()
        start_time, end_time = aggregator.get_time_range()
        aggregator.close()
        
        # Count articles in current prediction time range
        articles_in_range = session.query(News).filter(
            and_(
                News.time_published >= start_time,
                News.time_published <= end_time
            )
        ).count()
        
        result = {
            'success': True,
            'data_status': {
                'latest_news_time': latest_news.time_published.isoformat() if latest_news else None,
                'news_today': news_today,
                'total_news': total_news,
                'articles_in_prediction_range': articles_in_range,
                'prediction_time_range': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                },
                'system_time': datetime.now().isoformat()
            }
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()

if __name__ == '__main__':
    app.run(debug=True, port=5001) 