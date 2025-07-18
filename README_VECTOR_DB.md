# FAISS Vector Database for Financial News

This system implements a semantic search engine using FAISS (Facebook AI Similarity Search) to enable fast similarity search over financial news articles from 2017-2023.

## Features

- **Semantic Search**: Find news articles by meaning, not just keywords
- **Ticker Analysis**: Search for news mentioning specific stock tickers with price change data
- **Price Impact Tracking**: Each news article includes percentage price changes for mentioned tickers
- **Persistent Storage**: FAISS index is saved to disk and loaded on server startup
- **REST API**: Easy-to-use HTTP endpoints for integration

## Architecture

```
Financial News Data (JSON) → Embeddings (SentenceTransformers) → FAISS Index → API Endpoints
                           ↓
                    Database (NewsFaiss table) ← Ticker Price Changes
```

## Setup and Installation

### 1. Install Dependencies

The required dependencies are already added to `requirements.txt`:
- `faiss-cpu>=1.7.4`
- `sentence-transformers>=2.2.2`

Install them:
```bash
pip install -r requirements.txt
```

### 2. Create the Vector Database

Manually clone this repo into the base SNP500-Prediction-Model
https://github.com/felixdrinkall/financial-news-dataset#

Then cd into the financial-news-dataset and run the following command to decompress the json files 

xz -d data/*.xz

Process all financial news data and create the FAISS index:

```bash
python backfill_vector_db.py
```

This will:
- Process all JSON files in `financial-news-dataset/data/`
- Generate embeddings for title + description of each article
- Calculate percentage price changes for mentioned tickers
- Store everything in the database and FAISS index
- Save the FAISS index to disk (`faiss_index.bin` and `faiss_mapping.pkl`)

**Note**: This process may take some time depending on your hardware and the amount of data.

### 3. Test the System

Run the test suite to verify everything works:

```bash
python test_vector_db.py
```

### 4. Start the Server

```bash
python app.py
```

The vector database will be automatically loaded when the server starts.

## API Endpoints

### 1. Semantic Search

Search for articles by meaning/content:

```bash
curl -X POST http://localhost:5001/api/vector/search \
     -H 'Content-Type: application/json' \
     -d '{
       "query": "Apple iPhone sales declining",
       "k": 10
     }'
```

**Response:**
```json
{
  "success": true,
  "query": "Apple iPhone sales declining",
  "results": [
    {
      "id": 12345,
      "title": "Apple Reports Lower iPhone Sales in Q3",
      "description": "Apple Inc. reported a decline in iPhone sales...",
      "date_publish": "2023-05-15T10:30:00",
      "ticker_metadata": {
        "AAPL": -2.5
      },
      "similarity_score": 0.89
    }
  ],
  "total_found": 10
}
```

### 2. Search by Ticker

Find articles mentioning a specific stock ticker:

```bash
curl http://localhost:5001/api/vector/search_by_ticker/AAPL?k=5
```

**Response:**
```json
{
  "success": true,
  "ticker": "AAPL",
  "results": [
    {
      "id": 12345,
      "title": "Apple Announces New Product Line",
      "description": "Apple Inc. unveiled its latest...",
      "date_publish": "2023-05-15T10:30:00",
      "ticker_metadata": {
        "AAPL": 3.2,
        "MSFT": -0.5
      },
      "price_change_pct": 3.2
    }
  ],
  "total_found": 5
}
```

### 3. Database Statistics

Get information about the vector database:

```bash
curl http://localhost:5001/api/vector/stats
```

**Response:**
```json
{
  "success": true,
  "stats": {
    "total_records": 250000,
    "faiss_index_size": 250000,
    "model_name": "all-MiniLM-L6-v2",
    "date_range": {
      "start": "2017-01-01T00:00:00",
      "end": "2023-12-31T23:59:59"
    }
  }
}
```

### 4. Recent News

Get recent news articles:

```bash
curl "http://localhost:5001/api/vector/recent_news?days=30&limit=20"
```

## Data Structure

### NewsFaiss Table

Each record in the database contains:

- `id`: Primary key
- `faiss_id`: Index in the FAISS vector space
- `date_publish`: Publication date of the news article
- `title`: Article title
- `description`: Article description/summary
- `ticker_metadata`: JSON object with ticker price changes

### Ticker Metadata Format

```json
{
  "AAPL": 2.5,    // +2.5% price change from current day to next day
  "GOOGL": -1.2,  // -1.2% price change
  "TSLA": 0.0     // No change
}
```

The percentage change is calculated as:
```
((next_day_price - curr_day_price) / curr_day_price) * 100
```

## Python Usage

### Direct Usage

```python
from models.vector_db import search_news, search_by_ticker, vector_search

# Semantic search
results = search_news("Tesla production issues", k=5)
for news, similarity in results:
    print(f"{news.title} (similarity: {similarity:.3f})")

# Search by ticker
results = search_by_ticker("TSLA", k=5)
for news, price_change in results:
    print(f"{news.title} (price change: {price_change:+.2f}%)")

# Get database stats
stats = vector_search.get_stats()
print(f"Total records: {stats['total_records']}")
```

### Advanced Usage

```python
from models.vector_db import VectorSearchEngine

# Create custom instance
engine = VectorSearchEngine(model_name='all-mpnet-base-v2')
engine.load()

# Perform searches
results = engine.search("cryptocurrency regulation", k=10)
```

## Performance Considerations

- **Index Type**: Uses HNSW (Hierarchical Navigable Small World) for fast approximate search
- **Embedding Model**: `all-MiniLM-L6-v2` (384 dimensions) for good balance of speed and quality
- **Memory Usage**: FAISS index is loaded into memory for fast search
- **Disk Storage**: Index files are ~100-500MB depending on data size

## Troubleshooting

### Vector Database Not Loading

**Error**: `Vector search engine not available`

**Solutions**:
1. Run `python backfill_vector_db.py` to create the index
2. Check that `faiss_index.bin` and `faiss_mapping.pkl` exist in the project root
3. Verify dependencies are installed: `pip install faiss-cpu sentence-transformers`

### Memory Issues

If you encounter memory issues during processing:

1. Process data in smaller batches by modifying `backfill_vector_db.py`
2. Use a smaller embedding model (e.g., `all-MiniLM-L12-v2` → `all-MiniLM-L6-v2`)
3. Consider using `faiss-gpu` for faster processing if you have a GPU

### Search Quality Issues

To improve search quality:

1. Try different embedding models in `models/vector_db.py`
2. Adjust the search parameters (k value, similarity thresholds)
3. Preprocess queries (remove stop words, normalize text)

## File Structure

```
├── backfill_vector_db.py          # Script to create/populate vector DB
├── models/
│   ├── vector_db.py               # Vector search engine utilities
│   └── database.py                # Database models (includes NewsFaiss)
├── test_vector_db.py              # Test suite
├── faiss_index.bin                # FAISS index file (created after backfill)
├── faiss_mapping.pkl              # ID mapping file (created after backfill)
└── financial-news-dataset/
    └── data/                      # Source JSON files
        ├── 2017_processed.json
        ├── 2018_processed.json
        └── ...
```

## Next Steps

1. **Run the backfill**: `python backfill_vector_db.py`
2. **Test the system**: `python test_vector_db.py`
3. **Start the server**: `python app.py`
4. **Try the API endpoints** using the examples above

The vector database enables powerful semantic search capabilities for your financial news analysis system! 