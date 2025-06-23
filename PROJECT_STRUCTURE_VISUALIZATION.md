# 📊 SNP500 Prediction Model - Project Structure

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SNP500 PREDICTION MODEL                      │
│                    Trading Simulation System                    │
└─────────────────────────────────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
   ┌────▼────┐           ┌────▼────┐           ┌────▼────┐
   │   WEB   │           │  CORE   │           │  DATA   │
   │   UI    │           │ ENGINE  │           │ LAYER   │
   └─────────┘           └─────────┘           └─────────┘
```

## 📁 Directory Structure

```
SNP500-Prediction-Model/
├── 🌐 Frontend (React)
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.js     # Main simulation overview
│   │   │   ├── Simulation.js    # Individual simulation details
│   │   │   └── Day.js          # Daily trading breakdown
│   │   ├── App.js              # React root component
│   │   └── index.js            # React entry point
│   ├── public/                 # Static assets
│   └── package.json            # Node.js dependencies
│
├── 🧠 Models (AI/ML Core)
│   ├── base_sentiment_model.py # Sentiment analysis engine
│   ├── stock_simulation.py     # Trading simulation logic
│   └── database.py            # SQLAlchemy ORM models
│
├── 📊 Data Fetchers
│   ├── alphavantage_fetcher.py # News & market data
│   ├── stock_price_fetcher.py  # Stock price data
│   ├── newsapi_fetcher.py      # Alternative news source
│   └── finnhub_fetcher.py      # Financial data API
│
├── 💾 Data Storage
│   ├── trading_data.db         # SQLite database (82MB)
│   ├── alpha_vantage_news_*.json # News archives
│   └── stock_prices.db         # Historical price data
│
├── 🎯 Results
│   └── simulation_summaries.json # Performance metrics
│
├── 🐍 Core Scripts
│   ├── app.py                  # Flask web server
│   ├── run_simulation.py       # Simulation orchestrator
│   └── query_simulation_example.py # Data query examples
│
└── ⚙️ Configuration
    ├── requirements.txt        # Python dependencies
    ├── setup.sh               # Environment setup
    ├── start.sh / stop.sh     # Service management
    └── webpack.config.js      # Frontend build config
```

## 🔄 Data Flow Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   📰 NEWS APIs  │    │  📈 STOCK APIs  │    │  💾 DATABASE    │
│                 │    │                 │    │                 │
│ • Alpha Vantage │    │ • Alpha Vantage │    │ • News          │
│ • NewsAPI       │    │ • Finnhub       │    │ • Stock Prices  │
│ • Financial     │    │ • Market Data   │    │ • Simulations   │
└─────────┬───────┘    └─────────┬───────┘    │ • Sentiment     │
          │                      │            └─────────┬───────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   🧠 SENTIMENT MODEL                            │
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│  │   EXTRACT   │───▶│   ANALYZE   │───▶│  GENERATE   │       │
│  │   TICKERS   │    │ SENTIMENT   │    │  SIGNALS    │       │
│  │             │    │             │    │             │       │
│  │ • Regex     │    │ • FinBERT   │    │ • Long/Short│       │
│  │ • Keywords  │    │ • Score     │    │ • Balanced  │       │
│  └─────────────┘    └─────────────┘    └─────────────┘       │
└─────────────────────────────────────────────┬───────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  💰 TRADING SIMULATION                          │
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│  │    OPEN     │───▶│    TRADE    │───▶│    CLOSE    │       │
│  │ POSITIONS   │    │   EXECUTE   │    │ POSITIONS   │       │
│  │             │    │             │    │             │       │
│  │ • Market    │    │ • $10k each │    │ • Calculate │       │
│  │   Open      │    │ • Long/Short│    │   P&L       │       │
│  └─────────────┘    └─────────────┘    └─────────────┘       │
└─────────────────────────────────────────────┬───────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    📊 WEB INTERFACE                             │
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│  │ DASHBOARD   │    │ SIMULATION  │    │    DAY      │       │
│  │             │    │   DETAILS   │    │  DETAILS    │       │
│  │ • All Runs  │    │ • Daily P&L │    │ • Trades    │       │
│  │ • Metrics   │    │ • Performance│    │ • News      │       │
│  │ • Charts    │    │ • Positions │    │ • Sentiment │       │
│  └─────────────┘    └─────────────┘    └─────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

## 🔧 Technical Stack

### Backend (Python)
```
┌──────────────────┐
│  🐍 PYTHON CORE  │
├──────────────────┤
│ • Flask          │ ← Web server
│ • SQLAlchemy     │ ← Database ORM
│ • Transformers   │ ← AI models (FinBERT)
│ • PyTorch        │ ← ML framework
│ • Pandas/NumPy   │ ← Data processing
│ • Requests       │ ← API calls
└──────────────────┘
```

### Frontend (JavaScript)
```
┌──────────────────┐
│  ⚛️ REACT UI     │
├──────────────────┤
│ • React          │ ← UI framework
│ • Webpack        │ ← Module bundler
│ • CSS3           │ ← Styling
│ • Fetch API      │ ← Backend communication
└──────────────────┘
```

### Database (SQLite)
```
┌──────────────────┐
│  💾 DATA SCHEMA  │
├──────────────────┤
│ • simulations    │ ← Simulation runs
│ • daily_recap    │ ← Daily results
│ • news_sentiment │ ← Sentiment analysis
│ • stock_price    │ ← Historical prices
│ • news          │ ← News articles
└──────────────────┘
```

## 🎯 Core Components

### 1. **Sentiment Analysis Engine**
- **Purpose**: Convert news → trading signals
- **Input**: News headlines
- **Process**: Extract tickers → Analyze sentiment → Generate balanced long/short signals
- **Output**: Daily trading recommendations

### 2. **Trading Simulator**
- **Purpose**: Execute virtual trades and track performance
- **Strategy**: Market-neutral (equal long/short positions)
- **Position Size**: Fixed $10,000 per position
- **Timeframe**: Intraday (open at market open, close at market close)

### 3. **Web Dashboard**
- **Purpose**: Visualize simulation results
- **Features**: Performance metrics, daily breakdowns, trade analysis
- **Real-time**: Live updates from SQLite database

### 4. **Data Pipeline**
- **Purpose**: Collect and process market data
- **Sources**: Alpha Vantage, NewsAPI, Finnhub
- **Storage**: SQLite database with historical data

## 📈 Key Features

- ✅ **Automated News Analysis**: FinBERT sentiment model
- ✅ **Market-Neutral Strategy**: Balanced long/short positions  
- ✅ **Historical Backtesting**: 2022-2024 simulation periods
- ✅ **Web Interface**: React-based dashboard
- ✅ **Performance Metrics**: Sharpe ratio, drawdown, win rate
- ✅ **Real-time Updates**: Live simulation monitoring

## 🚀 Deployment

```bash
# Setup
./setup.sh              # Install dependencies
./start.sh               # Start services
# Frontend: http://localhost:3000
# Backend:  http://localhost:5001

# Usage
python run_simulation.py  # Run new simulation
python app.py            # Start web server
```

---
**Generated**: $(date)
**Database Size**: 82MB (trading_data.db)
**Simulation Range**: March 2022 - March 2024
**Strategy**: Sentiment-driven market-neutral trading 