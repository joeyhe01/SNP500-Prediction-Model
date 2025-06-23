# Realtime Trading Setup Guide

## Overview

The realtime trading feature uses multiple news APIs to aggregate financial news and generate trading predictions using sentiment analysis. This provides a comprehensive view of market sentiment by combining data from:

1. **Alpha Vantage** (already configured) - Financial news & sentiment
2. **NewsAPI** - Broad financial news sources  
3. **Finnhub** - Market news with sentiment analysis
4. **Polygon.io** - Real-time financial news
5. **Financial Modeling Prep** - Company-specific news

## API Keys Setup

### 1. Alpha Vantage (Already Configured)
- ✅ Already set up with key: `KWL2J50Q32KS3YSM`
- No additional setup needed

### 2. NewsAPI (Optional but recommended)
1. Visit: https://newsapi.org/
2. Create a free account
3. Get your API key
4. Set environment variable: `export NEWSAPI_KEY=your_api_key_here`

### 3. Finnhub (Optional but recommended)
1. Visit: https://finnhub.io/
2. Create a free account
3. Get your API key from the dashboard
4. Set environment variable: `export FINNHUB_KEY=your_api_key_here`

### 4. Polygon.io (Optional)
1. Visit: https://polygon.io/
2. Create a free account
3. Get your API key
4. Set environment variable: `export POLYGON_KEY=your_api_key_here`

### 5. Financial Modeling Prep (Optional but recommended)
1. Visit: https://financialmodelingprep.com/
2. Create a free account
3. Get your API key
4. Set environment variable: `export FMP_KEY=your_api_key_here`

## Environment Variables Setup

### Option 1: Terminal (Temporary)
```bash
export NEWSAPI_KEY=your_newsapi_key
export FINNHUB_KEY=your_finnhub_key
export POLYGON_KEY=your_polygon_key
export FMP_KEY=your_fmp_key
```

### Option 2: Create .env file (Recommended)
Create a `.env` file in the project root:
```
NEWSAPI_KEY=your_newsapi_key
FINNHUB_KEY=your_finnhub_key  
POLYGON_KEY=your_polygon_key
FMP_KEY=your_fmp_key
```

Then load it in your shell:
```bash
source .env
```

### Option 3: Add to shell profile (Permanent)
Add to `~/.bashrc` or `~/.zshrc`:
```bash
export NEWSAPI_KEY=your_newsapi_key
export FINNHUB_KEY=your_finnhub_key
export POLYGON_KEY=your_polygon_key
export FMP_KEY=your_fmp_key
```

## Installation

1. Install new dependencies:
```bash
pip install -r requirements.txt
```

2. Initialize database with new tables:
```bash
python -c "from models.database import init_database; init_database()"
```

## Usage

### Frontend
1. Start the application: `./start.sh`
2. Navigate to http://localhost:3000
3. Click on the "🔴 Realtime Trading" tab
4. Click "🚀 Generate New Prediction" to analyze current news

### API Endpoints
- `POST /api/realtime/generate-prediction` - Generate new prediction
- `GET /api/realtime/latest-prediction` - Get latest prediction
- `GET /api/realtime/predictions` - Get recent predictions
- `GET /api/realtime/prediction-status` - Get system status

### Command Line Testing
```bash
# Test the news aggregator
python realtime/news_aggregator.py

# Test the full prediction pipeline
python realtime/realtime_predictor.py
```

## How It Works

### News Aggregation
The system pulls news from the previous day at 5 PM to either:
- Current time (if before 9 AM)
- Today at 9 AM (if after 9 AM)

This captures news that could affect the next trading day.

### Sentiment Analysis
- Uses the existing FinBERT model to analyze sentiment
- Extracts stock tickers from headlines using keyword matching
- Aggregates sentiment scores by ticker

### Trading Signals
- Generates up to 5 long positions (positive sentiment)
- Generates up to 5 short positions (negative sentiment)
- Balances positions (equal number of long/short)
- Provides signal strength and supporting article counts

## Rate Limits & Costs

### Free Tiers
- **Alpha Vantage**: 5 calls/minute (already using)
- **NewsAPI**: 1,000 requests/month  
- **Finnhub**: 60 requests/minute
- **Polygon**: 5 requests/minute
- **FMP**: Varies by plan

### Recommendations
- Start with 2-3 APIs for testing
- Monitor usage to stay within free limits
- Consider upgrading to paid plans for production use

## Troubleshooting

### No News Found
- Check API keys are set correctly
- Verify internet connection
- Check API rate limits

### No Trading Signals
- May happen if no articles mention specific tickers
- Try during market hours when more news is published
- Check that news sources cover financial topics

### Performance Issues
- Reduce number of APIs used
- Implement caching for repeated requests
- Consider running predictions less frequently

## System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   News APIs     │───▶│ News Aggregator  │───▶│ Sentiment Model │
│ (5 sources)     │    │                  │    │ (FinBERT)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
┌─────────────────┐    ┌──────────────────┐             │
│   Database      │◀───│ Trading Signals  │◀────────────┘
│ (Predictions)   │    │ Generator        │
└─────────────────┘    └──────────────────┘
                                │
┌─────────────────┐             │
│ Frontend UI     │◀────────────┘
│ (React)         │
└─────────────────┘
```

The system is designed to work with any combination of the APIs - if some are not configured, it will skip them and continue with available sources. 