import pandas as pd
from datetime import datetime, timedelta
from data_fetchers.stock_price_fetcher import StockPriceFetcher
from models.base_sentiment_model import BaseSentimentModel
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
            self.model = model_class()
        self.price_fetcher = StockPriceFetcher()
        self.portfolio_value = 100000  # Starting with $100k
        self.position_size = position_size  # Fixed position size
        self.positions = {'long': {}, 'short': {}}
        self.trade_history = []
        self.daily_returns = []
        self.daily_positions = []  # Track daily long/short positions
        self.daily_detailed_results = []  # NEW: Track detailed daily results with individual stock performance
        
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
    
    def execute_trades(self, date, signals):
        """
        Execute trades based on signals
        
        Args:
            date: Trading date
            signals: Dict with 'long' and 'short' ticker lists
        """
        # Close existing positions and get detailed results
        daily_details = self.close_all_positions_with_details(date)
        
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
            return
        
        position_size = self.position_size  # Fixed position size
        
        # Open long positions
        for ticker in signals['long']:
            price_data = self.price_fetcher.get_stock_price(ticker, date)
            if price_data and price_data['open'] > 0:
                shares = position_size / price_data['open']
                self.positions['long'][ticker] = {
                    'shares': shares,
                    'entry_price': price_data['open'],
                    'entry_date': date
                }
                
                self.trade_history.append({
                    'date': date,
                    'ticker': ticker,
                    'action': 'BUY',
                    'shares': shares,
                    'price': price_data['open'],
                    'value': position_size
                })
        
        # Open short positions
        for ticker in signals['short']:
            price_data = self.price_fetcher.get_stock_price(ticker, date)
            if price_data and price_data['open'] > 0:
                shares = position_size / price_data['open']
                self.positions['short'][ticker] = {
                    'shares': shares,
                    'entry_price': price_data['open'],
                    'entry_date': date
                }
                
                self.trade_history.append({
                    'date': date,
                    'ticker': ticker,
                    'action': 'SHORT',
                    'shares': shares,
                    'price': price_data['open'],
                    'value': position_size
                })
    
    def close_all_positions_with_details(self, date):
        """
        Close all open positions at market open and return detailed position information
        
        Returns:
            Dictionary with detailed position results for the day
        """
        daily_pnl = 0
        position_details = []
        
        # Close long positions
        for ticker, position in list(self.positions['long'].items()):
            price_data = self.price_fetcher.get_stock_price(ticker, date)
            if price_data and price_data['open'] > 0:
                entry_price = position['entry_price']
                exit_price = price_data['open']
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
                
                del self.positions['long'][ticker]
        
        # Close short positions
        for ticker, position in list(self.positions['short'].items()):
            price_data = self.price_fetcher.get_stock_price(ticker, date)
            if price_data and price_data['open'] > 0:
                entry_price = position['entry_price']
                exit_price = price_data['open']
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
                
                del self.positions['short'][ticker]
        
        # Update portfolio value
        self.portfolio_value += daily_pnl
        
        # Store detailed daily results
        if position_details:
            daily_detail = {
                'date': date,
                'total_pnl': daily_pnl,
                'portfolio_value': self.portfolio_value,
                'return_pct': (daily_pnl / (self.portfolio_value - daily_pnl)) * 100,
                'positions': position_details
            }
            self.daily_detailed_results.append(daily_detail)
        
        if daily_pnl != 0:
            self.daily_returns.append({
                'date': date,
                'pnl': daily_pnl,
                'portfolio_value': self.portfolio_value,
                'return_pct': (daily_pnl / (self.portfolio_value - daily_pnl)) * 100
            })
        
        return position_details

    def close_all_positions(self, date):
        """
        Close all open positions at market open (legacy method for compatibility)
        """
        return self.close_all_positions_with_details(date)
    
    def run_simulation(self, start_date, end_date):
        """
        Run the simulation for the specified date range
        
        Args:
            start_date: Start date (datetime.date)
            end_date: End date (datetime.date)
        """
        print(f"Running simulation from {start_date} to {end_date}")
        print(f"Starting portfolio value: ${self.portfolio_value:,.2f}")
        
        trading_days = self.get_trading_days(start_date, end_date)
        
        for i, date in enumerate(trading_days):
            # Skip first day (need previous day for signals)
            if i == 0:
                continue
                
            # Get trading signals from the model
            signals = self.model.get_trading_signals(date)
            
            # Execute trades
            if signals['long'] or signals['short']:
                self.execute_trades(date, signals)
            
            # Progress update
            if i % 20 == 0:
                print(f"Progress: {i}/{len(trading_days)} days, Portfolio: ${self.portfolio_value:,.2f}")
        
        # Close any remaining positions
        if trading_days:
            self.close_all_positions(trading_days[-1])
        
        print(f"\nSimulation complete!")
        print(f"Final portfolio value: ${self.portfolio_value:,.2f}")
        print(f"Total return: {((self.portfolio_value - 100000) / 100000) * 100:.2f}%")
    
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
        Save simulation results to file
        """
        results = {
            'starting_portfolio_value': 100000,  # Starting capital
            'metrics': self.calculate_metrics(),
            'daily_returns': self.daily_returns,
            'daily_positions': self.daily_positions,  # Include long/short positions
            'daily_detailed_results': self.daily_detailed_results,  # NEW: Detailed daily results with individual stock performance
            'trade_history': self.trade_history
        }
        
        os.makedirs('results', exist_ok=True)
        filepath = os.path.join('results', filename)
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"Results saved to {filepath}")
    
    def compare_to_sp500(self, start_date, end_date):
        """
        Compare performance to S&P 500
        """
        # For demonstration, we'll use SPY as a proxy for S&P 500
        spy_start = self.price_fetcher.get_stock_price('SPY', start_date)
        spy_end = self.price_fetcher.get_stock_price('SPY', end_date)
        
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
        self.price_fetcher.close() 