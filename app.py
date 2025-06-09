#!/usr/bin/env python3
"""
Flask web application for S&P 500 trading simulation analysis
"""

from flask import Flask, jsonify, request, send_from_directory, send_file
from models.database import get_db_session
from models.database import Simulation, DailyRecap, NewsSentiment, News
from sqlalchemy import desc, asc, func, cast, Date
from datetime import datetime, timedelta
import json
import os
from sqlalchemy.orm import aliased

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

if __name__ == '__main__':
    app.run(debug=True, port=5001) 