# LLM-Based Sentiment Analysis Implementation

This document describes the implementation of the new LLM-based sentiment analysis system that replaces the previous string matching approach.

## Overview

The system has been updated to use OpenAI's GPT-4o-mini model for sentiment analysis instead of the previous approach that used:
- String matching for ticker extraction
- FinBERT for sentiment analysis

## New Approach

The new `LLMSentimentModel` class uses OpenAI's API to:
1. Analyze news headlines and summaries
2. Identify multiple companies that may be affected by the news
3. Determine the sentiment impact (positive, negative, neutral) for each company
4. Return multiple ticker/sentiment pairs per news article

## Key Features

- **Multi-ticker extraction**: One news article can now affect multiple companies
- **Better accuracy**: Uses advanced language models to understand context and indirect effects
- **Smarter filtering**: Only includes S&P 500 companies for higher quality results
- **Flexible input**: Can analyze headlines alone or with summaries for better context

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install the new `openai>=1.0.0` package along with existing dependencies.

### 2. Set Up OpenAI API Key

The system requires an OpenAI API key to function. You can set it up in several ways:

#### Option A: Set environment variable permanently (Recommended)

For **macOS/Linux with zsh**:
```bash
echo 'export OPENAI_API_KEY="your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

For **macOS/Linux with bash**:
```bash
echo 'export OPENAI_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

#### Option B: Use the setup script
```bash
python setup_openai.py
```

This will set the API key for the current session and provide instructions for permanent setup.

#### Option C: Set for current session only
```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 3. Test the Implementation

Run the test script to verify everything works:

```bash
python test_llm_sentiment.py
```

This will test the LLM sentiment model with sample headlines and show the results.

## Usage

### Basic Usage

```python
from models.llm_sentiment_model import LLMSentimentModel

# Initialize the model
model = LLMSentimentModel(debug=True)

# Analyze a headline
headline = "Apple Reports Record Q4 Earnings, iPhone Sales Surge"
summary = "Apple Inc. reported strong quarterly results..."

results = model.analyze_news_sentiment(headline, summary)
# Returns: [{'ticker': 'AAPL', 'sentiment': 'positive'}]

# Close the model when done
model.close()
```

### Integration with Realtime Predictor

The `RealtimeTradingPredictor` has been updated to use the new LLM model automatically:

```python
from realtime.realtime_predictor import RealtimeTradingPredictor

# Initialize with LLM model
predictor = RealtimeTradingPredictor(debug=True)

# Run prediction (now uses LLM sentiment analysis)
result = predictor.run_realtime_prediction()
```

## Database Changes

The system continues to use the existing `NewsSentiment` table but now stores:
- Multiple rows per news article (one for each ticker/sentiment pair)
- Source information in `extra_data` field (`'source': 'openai_llm'`)
- All the same fields as before for backward compatibility

## Cost Considerations

- Uses GPT-4o-mini model for cost efficiency
- Approximately $0.15 per 1M input tokens, $0.60 per 1M output tokens
- Typical news analysis uses ~200-500 tokens per article
- Estimated cost: ~$0.0001-0.0003 per news article

## Error Handling

The system includes robust error handling:
- Graceful API failures (returns empty results)
- JSON parsing errors
- Invalid ticker format filtering
- Rate limiting awareness

## Configuration

Key configuration options in `LLMSentimentModel`:

- `debug=True`: Enable detailed logging
- Temperature: Set to 0.1 for consistent results
- Model: Uses `gpt-4o-mini` for cost efficiency
- S&P 500 filtering: Only returns tickers from major indices

## Comparison with Previous System

| Feature | Previous System | New LLM System |
|---------|----------------|----------------|
| Ticker Extraction | String matching | AI-powered analysis |
| Sentiment Analysis | FinBERT model | GPT-4o-mini |
| Tickers per Article | 1 | Multiple (typically 1-3) |
| Context Understanding | Limited | Advanced |
| Indirect Effects | Not captured | Captured |
| Cost | Free (local model) | ~$0.0001-0.0003 per article |
| Accuracy | Good for direct mentions | Excellent for all mentions |

## Files Changed

- `models/llm_sentiment_model.py` - New LLM sentiment model
- `realtime/realtime_predictor.py` - Updated to use LLM model
- `requirements.txt` - Added OpenAI dependency
- `setup_openai.py` - API key setup script
- `test_llm_sentiment.py` - Test script

## Monitoring and Debugging

Enable debug mode to see detailed analysis:

```python
model = LLMSentimentModel(debug=True)
```

This will show:
- OpenAI API responses
- Ticker filtering decisions
- Sentiment analysis results
- Processing statistics

## Troubleshooting

### Common Issues

1. **"OPENAI_API_KEY environment variable is required"**
   - Set the API key as described in setup instructions

2. **"No ticker-sentiment pairs found"**
   - Check if the news is about publicly traded companies
   - Verify companies are in S&P 500 index
   - Enable debug mode to see filtering decisions

3. **API Rate Limits**
   - The system handles rate limits gracefully
   - Consider adding delays between requests if needed

4. **High API Costs**
   - Monitor usage in OpenAI dashboard
   - Consider filtering news articles before analysis
   - Use headline-only analysis to reduce token usage

## Future Enhancements

Potential improvements:
- Caching of analysis results
- Batch processing for efficiency
- Confidence scores for predictions
- Support for additional stock indices
- Integration with vector databases for semantic search 