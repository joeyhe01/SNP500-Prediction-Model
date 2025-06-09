#!/usr/bin/env python3
"""
Main script to run stock trading simulations using sentiment analysis
"""

from datetime import datetime
from models.stock_simulation import StockSimulation
from models.base_sentiment_model import BaseSentimentModel
from models.database import init_database
import argparse
import sys

def run_yearly_simulation(year, model_class=BaseSentimentModel, debug=False):
    """
    Run simulation for a specific year
    
    Args:
        year: Year to simulate (2022 or 2023)
        model_class: Model class to use for trading signals
        debug: Whether to enable debug mode
    """
    print(f"\n{'='*60}")
    print(f"Running {year} Simulation ({model_class.__name__})")
    print(f"{'='*60}")
    
    # Define date ranges
    if year == 2022:
        start_date = datetime(2022, 3, 1).date()
        end_date = datetime(2023, 3, 1).date()
    elif year == 2023:
        start_date = datetime(2023, 3, 1).date()
        end_date = datetime(2024, 3, 1).date()
    else:
        raise ValueError(f"Invalid year: {year}")
    
    # Create and run simulation
    sim = StockSimulation(model_class, debug=debug)
    sim.run_simulation(start_date, end_date)
    
    # Calculate and display metrics
    metrics = sim.calculate_metrics()
    print(f"\n{year} Performance Metrics (Simulation ID: {sim.simulation_id}):")
    print(f"  Total Return: {metrics['total_return_pct']:.2f}%")
    print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
    print(f"  Win Rate: {metrics['win_rate_pct']:.2f}%")
    print(f"  Total Trades: {metrics['total_trades']}")
    
    # Compare to S&P 500
    sim.compare_to_sp500(start_date, end_date)
    
    # Save summary results (detailed data is in database)
    filename = f"{model_class.__name__}_{year}_summary.json"
    sim.save_results(filename)
    
    # Cleanup
    sim.cleanup()
    
    return sim, metrics

def run_combined_simulation(model_class=BaseSentimentModel, debug=False):
    """
    Run simulation for both 2022 and 2023 combined
    """
    print(f"\n{'='*60}")
    print(f"Running Combined 2022-2023 Simulation ({model_class.__name__})")
    print(f"{'='*60}")
    
    start_date = datetime(2022, 3, 1).date()
    end_date = datetime(2024, 3, 1).date()
    
    # Create and run simulation
    sim = StockSimulation(model_class, debug=debug)
    sim.run_simulation(start_date, end_date)
    
    # Calculate and display metrics
    metrics = sim.calculate_metrics()
    print(f"\nCombined 2022-2023 Performance Metrics (Simulation ID: {sim.simulation_id}):")
    print(f"  Total Return: {metrics['total_return_pct']:.2f}%")
    print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
    print(f"  Win Rate: {metrics['win_rate_pct']:.2f}%")
    print(f"  Total Trades: {metrics['total_trades']}")
    
    # Compare to S&P 500
    sim.compare_to_sp500(start_date, end_date)
    
    # Save summary results (detailed data is in database)
    filename = f"{model_class.__name__}_combined_2022_2023_summary.json"
    sim.save_results(filename)
    
    # Cleanup
    sim.cleanup()
    
    return sim, metrics

def main():
    parser = argparse.ArgumentParser(description='Run stock trading simulation')
    parser.add_argument('--model', type=str, default='BaseSentimentModel',
                        help='Model class name to use for simulation')
    parser.add_argument('--year', type=int, choices=[2022, 2023],
                        help='Specific year to simulate (if not specified, runs both)')
    parser.add_argument('--combined', action='store_true',
                        help='Run combined 2022-2023 simulation')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode to show ticker extraction details')
    
    args = parser.parse_args()
    
    # Initialize database
    print("Initializing database...")
    init_database()
    print("Database tables created/updated: stock_prices, news, simulation, news_sentiment, daily_recap")
    
    # Get model class
    if args.model == 'BaseSentimentModel':
        model_class = BaseSentimentModel
    else:
        # For future model implementations
        print(f"Error: Unknown model class: {args.model}")
        sys.exit(1)
    
    try:
        if args.combined:
            # Run combined simulation
            run_combined_simulation(model_class, debug=args.debug)
        elif args.year:
            # Run specific year
            run_yearly_simulation(args.year, model_class, debug=args.debug)
        else:
            # Run both years separately
            results_2022 = run_yearly_simulation(2022, model_class, debug=args.debug)
            results_2023 = run_yearly_simulation(2023, model_class, debug=args.debug)
            
            # Summary
            print(f"\n{'='*60}")
            print("SIMULATION SUMMARY")
            print(f"{'='*60}")
            print(f"2022 Total Return: {results_2022[1]['total_return_pct']:.2f}% (Simulation ID: {results_2022[0].simulation_id})")
            print(f"2023 Total Return: {results_2023[1]['total_return_pct']:.2f}% (Simulation ID: {results_2023[0].simulation_id})")
            
            # Also run combined for comparison
            print("\nRunning combined simulation for comparison...")
            run_combined_simulation(model_class, debug=args.debug)
            
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