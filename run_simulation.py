#!/usr/bin/env python3
"""
Main script to run stock trading simulations using sentiment analysis
"""

import os
# Fix tokenizer parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from datetime import datetime, date
from models.stock_simulation import StockSimulation
from models.llm_sentiment_model import LLMSentimentModel
from models.database import init_database
import argparse
import sys

def run_simulation(start_date, end_date, model_class=LLMSentimentModel, debug=False):
    """
    Run simulation for a specific date range
    
    Args:
        start_date: Start date for simulation (date object)
        end_date: End date for simulation (date object)
        model_class: Model class to use for trading signals
        debug: Whether to enable debug mode
    """
    print(f"\n{'='*60}")
    print(f"Running Simulation from {start_date} to {end_date} ({model_class.__name__})")
    print(f"{'='*60}")
    
    # Create and run simulation
    sim = StockSimulation(model_class, debug=debug)
    sim.run_simulation(start_date, end_date)
    
    # Calculate and display metrics
    metrics = sim.calculate_metrics()
    print(f"\nPerformance Metrics (Simulation ID: {sim.simulation_id}):")
    print(f"  Total Return: {metrics['total_return_pct']:.2f}%")
    print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
    print(f"  Win Rate: {metrics['win_rate_pct']:.2f}%")
    print(f"  Total Trades: {metrics['total_trades']}")
    
    # Compare to S&P 500
    sim.compare_to_sp500(start_date, end_date)
    
    # Save summary results (detailed data is in database)
    date_range = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
    filename = f"{model_class.__name__}_{date_range}_summary.json"
    sim.save_results(filename)
    
    # Cleanup
    sim.cleanup()
    
    return sim, metrics



def main():
    parser = argparse.ArgumentParser(description='Run stock trading simulation')
    parser.add_argument('--model', type=str, default='llm_sentiment_model',
                        help='Model class name to use for simulation')
    parser.add_argument('--start-date', type=str, default='2025-06-01',
                        help='Start date for simulation in YYYY-MM-DD format (default: 2025-06-01)')
    parser.add_argument('--end-date', type=str, default='2025-06-30',
                        help='End date for simulation in YYYY-MM-DD format (default: 2025-06-30)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode to show ticker extraction details')
    
    args = parser.parse_args()
    
    # Parse dates
    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
    except ValueError:
        print("Error: Invalid date format. Use YYYY-MM-DD format.")
        sys.exit(1)
    
    # Validate date range
    if start_date >= end_date:
        print("Error: Start date must be before end date.")
        sys.exit(1)
    
    # Initialize database
    print("Initializing database...")
    init_database()
    print("Database tables created/updated: stock_prices, news, simulation, news_sentiment, daily_recap")
    
    # Get model class
    if args.model == 'llm_sentiment_model':
        model_class = LLMSentimentModel
    else:
        # For future model implementations
        print(f"Error: Unknown model class: {args.model}")
        sys.exit(1)
    
    try:
        # Run simulation for the specified date range
        sim, metrics = run_simulation(start_date, end_date, model_class, debug=args.debug)
            
        print(f"\n{'='*60}")
        print("SIMULATION COMPLETED")
        print(f"{'='*60}")
        print(f"Date Range: {start_date} to {end_date}")
        print(f"Model Used: {model_class.__name__}")
        print(f"Simulation ID: {sim.simulation_id}")
        print(f"Total Return: {metrics['total_return_pct']:.2f}%")
        
        print(f"\n{'='*60}")
        print("DATA STORAGE INFORMATION")
        print(f"{'='*60}")
        print("Detailed simulation data is stored in database tables:")
        print("  📊 simulation: Simulation metadata and final results")
        print("  📊 news_sentiment: Individual headline sentiment analysis")
        print("     - Each headline's sentiment, extracted ticker, and simulation ID")
        print("  📈 daily_recap: Daily trading results and portfolio performance")
        print("     - Daily P&L, positions, and detailed trade information by simulation")
        print("  💰 Only summary metrics are saved to JSON files")
        print(f"{'='*60}")
            
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError during simulation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 