#!/usr/bin/env python3
"""
Test script for FAISS Vector Database

This script demonstrates how to use the vector database for semantic search
and validates that everything is working correctly.
"""

import json
from models.vector_db import vector_search, search_news, search_by_ticker
from models.database import get_db_session, NewsFaiss


def test_basic_functionality():
    """Test basic vector database functionality"""
    print("=" * 60)
    print("TESTING VECTOR DATABASE FUNCTIONALITY")
    print("=" * 60)
    
    # Test loading
    print("\n1. Testing vector database loading...")
    if vector_search.is_loaded:
        print("✓ Vector database already loaded")
    else:
        success = vector_search.load()
        if success:
            print("✓ Vector database loaded successfully")
        else:
            print("✗ Could not load vector database")
            print("   Run 'python backfill_vector_db.py' first to create it.")
            return False
    
    # Get stats
    print("\n2. Getting database statistics...")
    stats = vector_search.get_stats()
    print(f"   Total records: {stats.get('total_records', 'N/A')}")
    print(f"   FAISS index size: {stats.get('faiss_index_size', 'N/A')}")
    print(f"   Model: {stats.get('model_name', 'N/A')}")
    print(f"   Date range: {stats.get('date_range', {}).get('start', 'N/A')} to {stats.get('date_range', {}).get('end', 'N/A')}")
    
    return True


def test_semantic_search():
    """Test semantic search functionality"""
    print("\n3. Testing semantic search...")
    
    test_queries = [
        "Apple iPhone sales declining",
        "Tesla electric vehicle production",
        "Amazon cloud computing revenue",
        "Microsoft Azure growth",
        "Google advertising business"
    ]
    
    for query in test_queries:
        print(f"\n   Query: '{query}'")
        results = search_news(query, k=3)
        
        if results:
            print(f"   Found {len(results)} results:")
            for i, (news, similarity) in enumerate(results[:2], 1):  # Show top 2
                print(f"     {i}. {news.title[:80]}...")
                print(f"        Similarity: {similarity:.3f}")
                print(f"        Date: {news.date_publish.strftime('%Y-%m-%d')}")
                if news.ticker_metadata:
                    print(f"        Tickers: {list(news.ticker_metadata.keys())}")
        else:
            print("   No results found")


def test_ticker_search():
    """Test ticker-based search functionality"""
    print("\n4. Testing ticker search...")
    
    test_tickers = ["AAPL", "TSLA", "GOOGL", "MSFT", "AMZN"]
    
    for ticker in test_tickers:
        print(f"\n   Ticker: {ticker}")
        results = search_by_ticker(ticker, k=3)
        
        if results:
            print(f"   Found {len(results)} articles:")
            for i, (news, price_change) in enumerate(results[:2], 1):  # Show top 2
                print(f"     {i}. {news.title[:80]}...")
                print(f"        Price change: {price_change:+.2f}%")
                print(f"        Date: {news.date_publish.strftime('%Y-%m-%d')}")
        else:
            print("   No articles found")


def test_recent_news():
    """Test recent news functionality"""
    print("\n5. Testing recent news retrieval...")
    
    recent_news = vector_search.get_recent_news(days=365, limit=5)  # Last year, top 5
    
    if recent_news:
        print(f"   Found {len(recent_news)} recent articles:")
        for i, news in enumerate(recent_news, 1):
            print(f"     {i}. {news.title[:80]}...")
            print(f"        Date: {news.date_publish.strftime('%Y-%m-%d')}")
            if news.ticker_metadata:
                tickers_with_changes = {k: v for k, v in news.ticker_metadata.items() if v != 0}
                if tickers_with_changes:
                    print(f"        Price changes: {tickers_with_changes}")
    else:
        print("   No recent articles found")


def demo_api_usage():
    """Demonstrate how to use the API endpoints"""
    print("\n6. API Usage Examples:")
    print("   Once your server is running (python app.py), you can use these endpoints:")
    print()
    print("   # Semantic search")
    print("   curl -X POST http://localhost:5001/api/vector/search \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{\"query\": \"Apple iPhone sales\", \"k\": 5}'")
    print()
    print("   # Search by ticker")
    print("   curl http://localhost:5001/api/vector/search_by_ticker/AAPL?k=5")
    print()
    print("   # Get database stats")
    print("   curl http://localhost:5001/api/vector/stats")
    print()
    print("   # Get recent news")
    print("   curl http://localhost:5001/api/vector/recent_news?days=30&limit=10")


def validate_data_quality():
    """Validate the quality of the processed data"""
    print("\n7. Data Quality Validation...")
    
    session = get_db_session()
    
    try:
        # Check for records with ticker metadata
        records_with_tickers = session.query(NewsFaiss).filter(
            NewsFaiss.ticker_metadata != '{}'
        ).limit(5).all()
        
        print(f"   Sample records with ticker price changes:")
        for i, record in enumerate(records_with_tickers, 1):
            print(f"     {i}. {record.title[:60]}...")
            print(f"        Date: {record.date_publish.strftime('%Y-%m-%d')}")
            print(f"        Ticker changes: {record.ticker_metadata}")
            print()
            
    except Exception as e:
        print(f"   Error validating data: {e}")
    finally:
        session.close()


def main():
    """Run all tests"""
    print("FAISS Vector Database Test Suite")
    print("================================")
    
    # Test basic functionality first
    if not test_basic_functionality():
        return
    
    # Run all other tests
    test_semantic_search()
    test_ticker_search() 
    test_recent_news()
    validate_data_quality()
    demo_api_usage()
    
    print("\n" + "=" * 60)
    print("TESTING COMPLETE")
    print("=" * 60)
    print("If all tests passed, your vector database is ready to use!")
    print("Start your server with: python app.py")
    print("Then you can use the API endpoints for semantic search.")


if __name__ == "__main__":
    main() 