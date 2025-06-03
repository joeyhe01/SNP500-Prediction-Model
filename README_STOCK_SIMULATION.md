# Stock Market Prediction Simulation System

This system implements a RAG-based approach for stock prediction using news sentiment analysis. It simulates trading strategies through 2022 (bear market) and 2023 (bull market) to evaluate performance.

## Architecture Overview

The system consists of several key components:

1. **Database Layer** (`models/database.py`)
   - SQLite database for caching stock price data and news articles
   - News table with indexed timestamp queries for efficient retrieval
   - Reduces API calls to Alpha Vantage

2. **Stock Price Fetcher** (`data_fetchers/stock_price_fetcher.py`)
   - Fetches daily stock prices from Alpha Vantage API
   - Caches data in local database
   - API Key: `KWL2J50Q32KS3YSM`

3. **News Fetcher** (`data_fetchers/alphavantage_fetcher.py`)
   - Fetches news from Alpha Vantage [News & Sentiments API](https://www.alphavantage.co/documentation/#news-sentiment)
   - Pulls news from multiple topics: earnings, financial_markets, finance, technology
   - Stores news in database with unique URL constraint
   - Fetches 50 headlines per topic per day

4. **Base Sentiment Model** (`models/base_sentiment_model.py`)
   - Uses Hugging Face's `ProsusAI/finbert` model
   - Analyzes news headlines for sentiment (positive/negative/neutral)
   - Extracts stock tickers from headlines
   - Generates trading signals (5 long, 5 short positions)
   - Queries news from database using timestamp ranges

5. **Simulation Framework** (`models/stock_simulation.py`)
   - Runs backtesting simulations
   - Tracks portfolio performance
   - Calculates metrics (Sharpe ratio, drawdown, etc.)
   - Compares to S&P 500 performance

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Initialize the database:
```bash
python -c "from models.database import init_database; init_database()"
```

3. Fetch news data (this will take a while due to API rate limits):
```bash
python data_fetchers/alphavantage_fetcher.py
```

Alternatively, if you have existing JSON news files, you can migrate them:
```bash
python migrate_json_to_db.py
```

4. Check news database status:
```bash
python check_news_db.py
```

## Usage

### Run Full Simulation (2022 and 2023)
```bash
python run_simulation.py
```

### Run Specific Year
```bash
python run_simulation.py --year 2022
python run_simulation.py --year 2023
```

### Run Combined 2022-2023 Simulation
```bash
python run_simulation.py --combined
```

### Use Different Model (for future implementations)
```bash
python run_simulation.py --model YourModelClassName
```

## How It Works

1. **Daily Trading Logic**:
   - At market open, analyze news from previous market close (4 PM) to current open (9:30 AM)
   - Use sentiment analysis to score each stock mentioned in headlines
   - Select top 5 positive sentiment stocks to go long
   - Select top 5 negative sentiment stocks to short
   - Hold positions for one day, then rebalance

2. **Sentiment Analysis**:
   - Headlines are processed through FinBERT (financial sentiment model)
   - Model returns sentiment classification
   - Scores are aggregated by ticker symbol

3. **Position Management**:
   - Equal-weight positions (portfolio value / number of positions)
   - Zero-cost strategy (equal long and short positions)
   - Daily rebalancing at market open

## Database Schema

### News Table
- `id`: Auto-incrementing primary key
- `title`: News headline
- `summary`: Article summary
- `source`: News source
- `url`: Article URL (unique constraint)
- `time_published`: Publication timestamp (indexed)

### StockPrice Table
- `ticker`: Stock symbol
- `date`: Trading date
- `open_price`: Opening price
- `close_price`: Closing price
- `high_price`: Daily high
- `low_price`: Daily low
- `volume`: Trading volume

## Output

The simulation produces:
- Console output with performance metrics
- JSON result files in `results/` directory containing:
  - Total return percentage
  - Sharpe ratio
  - Maximum drawdown
  - Win rate
  - Trade history
  - Daily returns

## Performance Metrics

- **Total Return**: Percentage gain/loss from initial $100,000
- **Sharpe Ratio**: Risk-adjusted return metric
- **Max Drawdown**: Largest peak-to-trough decline
- **Win Rate**: Percentage of profitable trades
- **Excess Return**: Performance vs S&P 500 (using SPY as proxy)

## Extending the System

To create a new model:

1. Create a new class in `models/` directory
2. Implement `get_trading_signals(self, date)` method
3. Return dict with 'long' and 'short' lists of tickers
4. Update `run_simulation.py` to import your model

Example:
```python
class YourCustomModel:
    def __init__(self):
        self.session = get_db_session()
        
    def get_trading_signals(self, date):
        # Your logic here
        return {
            'long': ['AAPL', 'MSFT', 'GOOGL'],
            'short': ['TSLA', 'META']
        }
    
    def close(self):
        self.session.close()
```

## Limitations

- Limited to stocks with news coverage
- Simple ticker extraction (could use NER models)
- No transaction costs or slippage modeling
- Assumes perfect execution at market open prices
- News quality depends on Alpha Vantage feed

## Future Enhancements

- Add more sophisticated NLP models
- Include technical indicators
- Model transaction costs and market impact
- Add risk management (stop losses, position sizing)
- Expand ticker coverage with better entity recognition
- Include sector/market analysis
- Real-time trading capabilities 