#!/usr/bin/env python3
"""
Simple example showing how to query simulation data from the database
"""

from models.database import get_db_session, Simulation, NewsSentiment, DailyRecap, News
from sqlalchemy import desc

def show_recent_simulations():
    """Show the most recent simulation runs"""
    session = get_db_session()
    
    print("=== Recent Simulations ===")
    simulations = session.query(Simulation).order_by(desc(Simulation.executed_at)).limit(5).all()
    
    for sim in simulations:
        print(f"Simulation {sim.id}: {sim.executed_at}")
        if sim.extra_data and 'metrics' in sim.extra_data:
            metrics = sim.extra_data['metrics']
            print(f"  Total Return: {metrics.get('total_return_pct', 0):.2f}%")
            print(f"  Total Trades: {metrics.get('total_trades', 0)}")
        print()
    
    session.close()

def show_simulation_details(simulation_id):
    """Show details for a specific simulation"""
    session = get_db_session()
    
    # Get simulation info
    sim = session.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not sim:
        print(f"Simulation {simulation_id} not found")
        return
    
    print(f"=== Simulation {simulation_id} Details ===")
    print(f"Executed: {sim.executed_at}")
    
    # Count sentiment records
    sentiment_count = session.query(NewsSentiment).filter(
        NewsSentiment.simulation_id == simulation_id
    ).count()
    
    # Count daily recap records  
    daily_count = session.query(DailyRecap).filter(
        DailyRecap.simulation_id == simulation_id
    ).count()
    
    print(f"Sentiment records: {sentiment_count}")
    print(f"Daily recap records: {daily_count}")
    
    # Show final metrics if available
    if sim.extra_data and 'metrics' in sim.extra_data:
        metrics = sim.extra_data['metrics']
        print(f"\nFinal Metrics:")
        print(f"  Total Return: {metrics.get('total_return_pct', 0):.2f}%")
        print(f"  Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"  Max Drawdown: {metrics.get('max_drawdown_pct', 0):.2f}%")
        print(f"  Win Rate: {metrics.get('win_rate_pct', 0):.2f}%")
        print(f"  Total Trades: {metrics.get('total_trades', 0)}")
    
    session.close()

def show_ticker_sentiment_summary(simulation_id, ticker):
    """Show sentiment summary for a specific ticker in a simulation"""
    session = get_db_session()
    
    sentiments = session.query(NewsSentiment).filter(
        NewsSentiment.simulation_id == simulation_id,
        NewsSentiment.ticker == ticker
    ).all()
    
    if not sentiments:
        print(f"No sentiment data found for {ticker} in simulation {simulation_id}")
        session.close()
        return
    
    print(f"=== {ticker} Sentiment in Simulation {simulation_id} ===")
    
    positive = len([s for s in sentiments if s.sentiment == 'positive'])
    negative = len([s for s in sentiments if s.sentiment == 'negative'])
    neutral = len([s for s in sentiments if s.sentiment == 'neutral'])
    total = len(sentiments)
    
    print(f"Total mentions: {total}")
    print(f"Positive: {positive} ({positive/total*100:.1f}%)")
    print(f"Negative: {negative} ({negative/total*100:.1f}%)")
    print(f"Neutral: {neutral} ({neutral/total*100:.1f}%)")
    
    session.close()

def main():
    """Example usage"""
    print("Stock Simulation Database Query Examples")
    print("=" * 50)
    
    # Show recent simulations
    show_recent_simulations()
    
    # If there are simulations, show details for the most recent one
    session = get_db_session()
    latest_sim = session.query(Simulation).order_by(desc(Simulation.executed_at)).first()
    session.close()
    
    if latest_sim:
        show_simulation_details(latest_sim.id)
        
        # Example: Show AAPL sentiment if available
        print(f"\nExample: AAPL sentiment analysis...")
        show_ticker_sentiment_summary(latest_sim.id, 'AAPL')
    else:
        print("No simulations found. Run a simulation first!")
        print("Example: python run_simulation.py --year 2022")

if __name__ == "__main__":
    main() 