from datetime import datetime, timedelta
from models.base_sentiment_model import BaseSentimentModel
from models.database import get_db_session, Simulation, DailyRecap, NewsSentiment, StockPrice
from sqlalchemy import and_
from sqlalchemy.orm.attributes import flag_modified
import pandas as pd
import json
import os

class StockSimulation:
    def __init__(self, model_class=BaseSentimentModel, debug=False, position_size=10000):
        """
        Initialize the simulation with a specific model class
        
        Args:
            model_class: The model class to use for generating trading signals
            debug: Whether to enable debug mode
            position_size: Fixed dollar amount per position (default: $10,000)
        """
        if model_class == BaseSentimentModel:
            self.model = model_class(debug=debug)
        else:
            # For LLMSentimentModel, pass debug parameter and enable multithreading
            try:
                self.model = model_class(debug=debug, max_workers=6)  # Use 6 threads for faster processing
            except TypeError:
                # Fallback for models that don't support max_workers parameter
                self.model = model_class(debug=debug)
        self.db_session = get_db_session()
        self.simulation_id = None  # Will be set when simulation starts
        self.portfolio_value = 100000  # Starting with $100k
        self.position_size = position_size  # Fixed position size
        self.positions = {'long': {}, 'short': {}}
        self.trade_history = []
        self.daily_returns = []
        self.daily_positions = []  # Track daily long/short positions
        self.daily_detailed_results = []  # NEW: Track detailed daily results with individual stock performance
        
    def create_simulation_record(self):
        """
        Create a new simulation record in the database
        
        Returns:
            int: The simulation ID
        """
        try:
            simulation = Simulation(
                executed_at=datetime.utcnow(),
                extra_data={}  # Will be populated with results later
            )
            self.db_session.add(simulation)
            self.db_session.commit()
            self.simulation_id = simulation.id
            print(f"Created simulation record with ID: {self.simulation_id}")
            return self.simulation_id
        except Exception as e:
            print(f"Error creating simulation record: {e}")
            self.db_session.rollback()
            raise
    
    def update_simulation_results(self, metrics):
        """
        Update the simulation record with final results
        
        Args:
            metrics: Dictionary containing simulation metrics
        """
        try:
            simulation = self.db_session.query(Simulation).filter(
                Simulation.id == self.simulation_id
            ).first()
            
            if simulation:
                simulation.extra_data = {
                    'metrics': metrics,
                    'completed_at': datetime.utcnow().isoformat(),
                    'total_trades': len(self.trade_history),
                    'trading_days': len(self.daily_returns)
                }
                self.db_session.commit()
                print(f"Updated simulation {self.simulation_id} with final results")
            else:
                print(f"Warning: Could not find simulation record {self.simulation_id}")
        except Exception as e:
            print(f"Error updating simulation results: {e}")
            self.db_session.rollback()
        
    def get_trading_days(self, start_date, end_date):
        """
        Get list of trading days (excluding weekends and major holidays)
        """
        trading_days = []
        current_date = start_date
        
        # Simple weekend exclusion (could be enhanced with holiday calendar)
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                trading_days.append(current_date)
            current_date += timedelta(days=1)
            
        return trading_days
    
    def get_stock_price(self, ticker, date):
        """
        Get stock price data for a specific ticker and date from the database
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            date: Date object
            
        Returns:
            Dictionary with price data or None if not found
        """
        try:
            stock_price = self.db_session.query(StockPrice).filter(
                and_(
                    StockPrice.ticker == ticker,
                    StockPrice.date == date
                )
            ).first()
            
            if stock_price:
                return {
                    'open': stock_price.open_price,
                    'close': stock_price.close_price,
                    'high': stock_price.high_price,
                    'low': stock_price.low_price,
                    'volume': stock_price.volume
                }
            else:
                print(f"Warning: No price data found for {ticker} on {date}")
                return None
                
        except Exception as e:
            print(f"Error fetching stock price for {ticker} on {date}: {e}")
            return None
    
    def store_daily_recap(self, date, starting_money, ending_money, positions_extra_data):
        """
        Store daily trading recap in the database
        
        Args:
            date: Trading date
            starting_money: Portfolio value at start of day
            ending_money: Portfolio value at end of day
            positions_extra_data: Dict containing shorts, longs, and returns for each position
        """
        try:
            # Check if we already have a recap for this date and simulation
            existing = self.db_session.query(DailyRecap).filter(
                and_(
                    DailyRecap.simulation_id == self.simulation_id,
                    DailyRecap.date == date
                )
            ).first()
            
            if existing:
                # Update existing record
                existing.starting_money = starting_money
                existing.ending_money = ending_money
                existing.extra_data = positions_extra_data
            else:
                # Create new record
                daily_recap = DailyRecap(
                    simulation_id=self.simulation_id,
                    date=date,
                    starting_money=starting_money,
                    ending_money=ending_money,
                    extra_data=positions_extra_data
                )
                self.db_session.add(daily_recap)
            
            self.db_session.commit()
        except Exception as e:
            print(f"Error storing daily recap: {e}")
            self.db_session.rollback()
    
    def execute_trades(self, date, signals):
        """
        Execute trades based on signals - OPEN positions at market open
        
        Args:
            date: Trading date
            signals: Dict with 'long' and 'short' ticker lists
        """
        starting_portfolio_value = self.portfolio_value
        daily_trades = []  # Track trades for this specific day
        
        # Record daily positions
        if signals['long'] or signals['short']:
            self.daily_positions.append({
                'date': date,
                'long': signals['long'].copy(),
                'short': signals['short'].copy()
            })
        
        # Calculate position size (fixed at $10,000 per position)
        total_positions = len(signals['long']) + len(signals['short'])
        if total_positions == 0:
            # Still store daily recap even if no trades
            self.store_daily_recap(date, starting_portfolio_value, self.portfolio_value, {
                'longs': [],
                'shorts': [],
                'positions': [],
                'trades': daily_trades,
                'daily_pnl': 0,
                'return_pct': 0
            })
            return
        
        position_size = self.position_size  # Fixed position size
        new_positions = []
        
        # Open long positions at market open
        for ticker in signals['long']:
            price_data = self.get_stock_price(ticker, date)
            if price_data and price_data['open'] > 0:
                shares = position_size / price_data['open']
                self.positions['long'][ticker] = {
                    'shares': shares,
                    'entry_price': price_data['open'],
                    'entry_date': date
                }
                
                trade = {
                    'date': date.strftime('%Y-%m-%d'),
                    'ticker': ticker,
                    'action': 'buy',
                    'shares': round(shares, 2),
                    'price': price_data['open'],
                    'total_value': round(position_size, 2),
                    'time': 'market_open'
                }
                
                self.trade_history.append({
                    'date': date,
                    'ticker': ticker,
                    'action': 'BUY',
                    'shares': shares,
                    'price': price_data['open'],
                    'value': position_size
                })
                
                daily_trades.append(trade)
                
                new_positions.append({
                    'ticker': ticker,
                    'position_type': 'long',
                    'shares': shares,
                    'entry_price': price_data['open'],
                    'position_value': position_size
                })
        
        # Open short positions at market open
        for ticker in signals['short']:
            price_data = self.get_stock_price(ticker, date)
            if price_data and price_data['open'] > 0:
                shares = position_size / price_data['open']
                self.positions['short'][ticker] = {
                    'shares': shares,
                    'entry_price': price_data['open'],
                    'entry_date': date
                }
                
                trade = {
                    'date': date.strftime('%Y-%m-%d'),
                    'ticker': ticker,
                    'action': 'sell',
                    'shares': round(shares, 2),
                    'price': price_data['open'],
                    'total_value': round(position_size, 2),
                    'time': 'market_open'
                }
                
                self.trade_history.append({
                    'date': date,
                    'ticker': ticker,
                    'action': 'SHORT',
                    'shares': shares,
                    'price': price_data['open'],
                    'value': position_size
                })
                
                daily_trades.append(trade)
                
                new_positions.append({
                    'ticker': ticker,
                    'position_type': 'short', 
                    'shares': shares,
                    'entry_price': price_data['open'],
                    'position_value': position_size
                })
        
        # Store opening trades only (P&L will be calculated at market close)
        positions_extra_data = {
            'longs': signals['long'],
            'shorts': signals['short'], 
            'positions': new_positions,
            'trades': daily_trades,
            'daily_pnl': 0,  # Will be updated at market close
            'return_pct': 0  # Will be updated at market close
        }
        
        self.store_daily_recap(date, starting_portfolio_value, self.portfolio_value, positions_extra_data)

    def close_positions_at_market_close(self, date):
        """
        Close all open positions at market close and calculate P&L
        
        Args:
            date: Trading date
        
        Returns:
            Daily P&L from closing positions
        """
        starting_portfolio_value = self.portfolio_value
        daily_pnl = 0
        closing_trades = []
        position_details = []
        
        # Close long positions at market close
        for ticker, position in list(self.positions['long'].items()):
            price_data = self.get_stock_price(ticker, date)
            if price_data and price_data['close'] > 0:
                entry_price = position['entry_price']
                exit_price = price_data['close']
                shares = position['shares']
                pnl = shares * (exit_price - entry_price)
                return_pct = ((exit_price - entry_price) / entry_price) * 100
                daily_pnl += pnl
                
                position_details.append({
                    'ticker': ticker,
                    'position_type': 'long',
                    'shares': shares,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'return_pct': return_pct,
                    'position_value': shares * entry_price
                })
                
                self.trade_history.append({
                    'date': date,
                    'ticker': ticker,
                    'action': 'SELL',
                    'shares': shares,
                    'price': exit_price,
                    'pnl': pnl
                })
                
                # Add closing trade
                closing_trade = {
                    'date': date.strftime('%Y-%m-%d'),
                    'ticker': ticker,
                    'action': 'sell',
                    'shares': round(shares, 2),
                    'price': exit_price,
                    'total_value': round(shares * exit_price, 2),
                    'time': 'market_close',
                    'pnl': round(pnl, 2)
                }
                closing_trades.append(closing_trade)
                
                del self.positions['long'][ticker]
        
        # Close short positions at market close
        for ticker, position in list(self.positions['short'].items()):
            price_data = self.get_stock_price(ticker, date)
            if price_data and price_data['close'] > 0:
                entry_price = position['entry_price']
                exit_price = price_data['close']
                shares = position['shares']
                # For shorts, profit when price goes down
                pnl = shares * (entry_price - exit_price)
                return_pct = ((entry_price - exit_price) / entry_price) * 100
                daily_pnl += pnl
                
                position_details.append({
                    'ticker': ticker,
                    'position_type': 'short',
                    'shares': shares,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'return_pct': return_pct,
                    'position_value': shares * entry_price
                })
                
                self.trade_history.append({
                    'date': date,
                    'ticker': ticker,
                    'action': 'COVER',
                    'shares': shares,
                    'price': exit_price,
                    'pnl': pnl
                })
                
                # Add closing trade
                closing_trade = {
                    'date': date.strftime('%Y-%m-%d'),
                    'ticker': ticker,
                    'action': 'buy',  # Covering a short is buying
                    'shares': round(shares, 2),
                    'price': exit_price,
                    'total_value': round(shares * exit_price, 2),
                    'time': 'market_close',
                    'pnl': round(pnl, 2)
                }
                closing_trades.append(closing_trade)
                
                del self.positions['short'][ticker]
        
        # Update portfolio value with daily P&L
        self.portfolio_value += daily_pnl
        
        # Update daily recap with closing trades and P&L
        if closing_trades or daily_pnl != 0:
            self.update_daily_recap_with_close(date, starting_portfolio_value, self.portfolio_value, 
                                              closing_trades, position_details, daily_pnl)
        
        # Store detailed daily results
        if position_details:
            daily_detail = {
                'date': date,
                'total_pnl': daily_pnl,
                'portfolio_value': self.portfolio_value,
                'return_pct': (daily_pnl / starting_portfolio_value) * 100 if starting_portfolio_value > 0 else 0,
                'positions': position_details
            }
            self.daily_detailed_results.append(daily_detail)
        
        if daily_pnl != 0:
            self.daily_returns.append({
                'date': date,
                'pnl': daily_pnl,
                'portfolio_value': self.portfolio_value,
                'return_pct': (daily_pnl / starting_portfolio_value) * 100 if starting_portfolio_value > 0 else 0
            })
        
        return daily_pnl

    def update_daily_recap_with_close(self, date, starting_money, ending_money, closing_trades, position_details, daily_pnl):
        """
        Update the daily recap with closing trade information and final P&L
        """
        try:
            existing = self.db_session.query(DailyRecap).filter(
                and_(
                    DailyRecap.simulation_id == self.simulation_id,
                    DailyRecap.date == date
                )
            ).first()
            
            if existing:
                # Get existing data and append closing trades
                extra_data = existing.extra_data or {}
                existing_trades = extra_data.get('trades', [])
                all_trades = existing_trades + closing_trades
                
                # Update with final data
                extra_data.update({
                    'trades': all_trades,
                    'closing_trades': closing_trades,
                    'positions': position_details,
                    'daily_pnl': daily_pnl,
                    'return_pct': ((ending_money - starting_money) / starting_money) * 100 if starting_money > 0 else 0
                })
                
                existing.ending_money = ending_money
                existing.extra_data = extra_data
                
                # CRITICAL: Flag the JSON field as modified so SQLAlchemy detects the change
                flag_modified(existing, 'extra_data')
                
                self.db_session.commit()
                
        except Exception as e:
            print(f"Error updating daily recap with close: {e}")
            import traceback
            traceback.print_exc()
            self.db_session.rollback()
    
    def run_simulation(self, start_date, end_date):
        """
        Run the simulation for the specified date range
        
        Args:
            start_date: Start date (datetime.date)
            end_date: End date (datetime.date)
        """
        # Create simulation record
        self.create_simulation_record()
        
        print(f"Running simulation {self.simulation_id} from {start_date} to {end_date}")
        print(f"Starting portfolio value: ${self.portfolio_value:,.2f}")
        
        trading_days = self.get_trading_days(start_date, end_date)
        
        for i, date in enumerate(trading_days):
            # Skip first day (need previous day for signals)
            if i == 0:
                continue
            
            # Get trading signals from the model for today
            signals = self.model.get_trading_signals(date, self.simulation_id)
            
            # Step 1: Open new positions at market open based on signals
            if signals['long'] or signals['short']:
                print(f"Opening positions for {date}: {len(signals['long'])} long, {len(signals['short'])} short")
                self.execute_trades(date, signals)
                
                # Step 2: Close positions at market close of the same day
                print(f"Closing positions at market close for {date}")
                daily_pnl = self.close_positions_at_market_close(date)
                print(f"Daily P&L: ${daily_pnl:,.2f}")
            else:
                print(f"No trading signals for {date}")
            
            # Progress update
            if i % 20 == 0:
                print(f"Progress: {i}/{len(trading_days)} days, Portfolio: ${self.portfolio_value:,.2f}")
        
        print(f"\nSimulation {self.simulation_id} complete!")
        print(f"Final portfolio value: ${self.portfolio_value:,.2f}")
        print(f"Total return: {((self.portfolio_value - 100000) / 100000) * 100:.2f}%")
        
        # Update simulation record with final results
        metrics = self.calculate_metrics()
        self.update_simulation_results(metrics)
    
    def calculate_metrics(self):
        """
        Calculate performance metrics
        """
        if not self.daily_returns:
            return {
                'starting_portfolio_value': 100000,
                'final_portfolio_value': self.portfolio_value,
                'total_return_pct': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown_pct': 0.0,
                'win_rate_pct': 0.0,
                'total_trades': 0
            }
        
        df = pd.DataFrame(self.daily_returns)
        
        total_return = ((self.portfolio_value - 100000) / 100000) * 100
        
        # Calculate Sharpe ratio (assuming 252 trading days per year)
        if len(df) > 0:
            daily_returns = df['return_pct'].values
            avg_daily_return = daily_returns.mean()
            std_daily_return = daily_returns.std()
            sharpe_ratio = (avg_daily_return * 252) / (std_daily_return * (252 ** 0.5)) if std_daily_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Calculate maximum drawdown
        cumulative_returns = (1 + df['return_pct'] / 100).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min() * 100
        
        # Win rate
        winning_trades = len([t for t in self.trade_history if t.get('pnl', 0) > 0])
        total_trades = len([t for t in self.trade_history if 'pnl' in t])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        metrics = {
            'starting_portfolio_value': 100000,
            'final_portfolio_value': self.portfolio_value,
            'total_return_pct': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_pct': max_drawdown,
            'win_rate_pct': win_rate,
            'total_trades': total_trades
        }
        
        return metrics
    
    def save_results(self, filename):
        """
        Save simplified simulation results to file (most data is now in database)
        """
        # Only save high-level summary metrics in JSON now
        results = {
            'simulation_summary': {
                'simulation_id': self.simulation_id,
                'starting_portfolio_value': 100000,
                'final_portfolio_value': self.portfolio_value,
                'simulation_date': datetime.now().isoformat(),
                'metrics': self.calculate_metrics()
            },
            'note': f'Detailed daily results and sentiment analysis are stored in database tables with simulation_id: {self.simulation_id}'
        }
        
        os.makedirs('results', exist_ok=True)
        filepath = os.path.join('results', filename)
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"Summary results saved to {filepath}")
        print(f"Detailed results are stored in database tables for simulation {self.simulation_id}:")
        print("  - news_sentiment: Individual headline sentiment analysis")
        print("  - daily_recap: Daily trading results and portfolio performance")
    
    def compare_to_sp500(self, start_date, end_date):
        """
        Compare performance to S&P 500
        """
        # For demonstration, we'll use SPY as a proxy for S&P 500
        spy_start = self.get_stock_price('SPY', start_date)
        spy_end = self.get_stock_price('SPY', end_date)
        
        if spy_start and spy_end:
            sp500_return = ((spy_end['close'] - spy_start['open']) / spy_start['open']) * 100
            strategy_return = ((self.portfolio_value - 100000) / 100000) * 100
            
            print(f"\nPerformance Comparison:")
            print(f"Strategy Return: {strategy_return:.2f}%")
            print(f"S&P 500 Return: {sp500_return:.2f}%")
            print(f"Excess Return: {strategy_return - sp500_return:.2f}%")
            
            return {
                'strategy_return': strategy_return,
                'sp500_return': sp500_return,
                'excess_return': strategy_return - sp500_return
            }
        
        return None
    
    def cleanup(self):
        """Clean up resources"""
        if hasattr(self.model, 'close'):
            self.model.close()
        self.db_session.close()

    def close_all_positions(self, date):
        """
        Legacy method for compatibility - closes positions at market close
        """
        return self.close_positions_at_market_close(date) 