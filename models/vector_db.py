"""
FAISS Vector Database Utility Module

This module provides easy access to the FAISS vector database for searching
financial news by semantic similarity.
"""

import os
import pickle
import numpy as np
from typing import List, Tuple, Optional
import faiss
from sentence_transformers import SentenceTransformer
from .database import get_db_session, NewsFaiss


class VectorSearchEngine:
    """FAISS-based semantic search engine for financial news"""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the vector search engine
        
        Args:
            model_name: Sentence transformer model name
        """
        self.model_name = model_name
        self.model = None
        self.index = None
        self.id_mapping = {}
        self.is_loaded = False
        
    def load(self, index_path: str = 'faiss_index.bin', mapping_path: str = 'faiss_mapping.pkl') -> bool:
        """
        Load the FAISS index and initialize the search engine
        
        Args:
            index_path: Path to the FAISS index file
            mapping_path: Path to the ID mapping file
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            if not os.path.exists(index_path) or not os.path.exists(mapping_path):
                print(f"FAISS files not found: {index_path}, {mapping_path}")
                return False
            
            # Load FAISS index
            self.index = faiss.read_index(index_path)
            
            # Load ID mapping
            with open(mapping_path, 'rb') as f:
                data = pickle.load(f)
                self.id_mapping = data['id_mapping']
                stored_model_name = data.get('model_name', self.model_name)
                
            # Initialize sentence transformer
            self.model = SentenceTransformer(stored_model_name)
            self.model_name = stored_model_name
            
            self.is_loaded = True
            print(f"Vector search engine loaded successfully")
            print(f"Index size: {self.index.ntotal} embeddings")
            print(f"Model: {self.model_name}")
            
            return True
            
        except Exception as e:
            print(f"Error loading vector search engine: {e}")
            return False
    
    def search(self, query: str, k: int = 10) -> List[Tuple[NewsFaiss, float]]:
        """
        Search for semantically similar news articles
        
        Args:
            query: Search query text
            k: Number of results to return
            
        Returns:
            List of (NewsFaiss record, similarity_score) tuples
        """
        if not self.is_loaded:
            print("Vector search engine not loaded. Call load() first.")
            return []
            
        if self.index.ntotal == 0:
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.model.encode([query], normalize_embeddings=True)
            query_embedding = query_embedding.astype('float32')
            
            # Search FAISS index
            distances, indices = self.index.search(query_embedding, min(k, self.index.ntotal))
            
            # Get database records
            session = get_db_session()
            results = []
            
            for distance, idx in zip(distances[0], indices[0]):
                if idx in self.id_mapping and idx != -1:
                    db_id = self.id_mapping[idx]
                    news_record = session.query(NewsFaiss).filter(NewsFaiss.id == db_id).first()
                    
                    if news_record:
                        similarity = 1.0 - distance  # Convert distance to similarity
                        results.append((news_record, float(similarity)))
            
            session.close()
            return results
            
        except Exception as e:
            print(f"Error during search: {e}")
            return []
    
    def search_by_ticker(self, ticker: str, k: int = 10) -> List[Tuple[NewsFaiss, float]]:
        """
        Search for news articles that mention a specific ticker
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'GOOGL')
            k: Number of results to return
            
        Returns:
            List of (NewsFaiss record, price_change) tuples
        """
        session = get_db_session()
        
        try:
            # Query database for records mentioning the ticker
            records = session.query(NewsFaiss).filter(
                NewsFaiss.ticker_metadata.contains(f'"{ticker}"')
            ).order_by(NewsFaiss.date_publish.desc()).limit(k).all()
            
            results = []
            for record in records:
                # Extract price change for this ticker
                price_change = record.ticker_metadata.get(ticker, 0.0)
                results.append((record, price_change))
            
            return results
            
        except Exception as e:
            print(f"Error searching by ticker: {e}")
            return []
        finally:
            session.close()
    
    def get_recent_news(self, days: int = 7, limit: int = 50) -> List[NewsFaiss]:
        """
        Get recent news articles
        
        Args:
            days: Number of days to look back
            limit: Maximum number of results
            
        Returns:
            List of NewsFaiss records
        """
        session = get_db_session()
        
        try:
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            
            records = session.query(NewsFaiss).filter(
                NewsFaiss.date_publish >= cutoff_date
            ).order_by(NewsFaiss.date_publish.desc()).limit(limit).all()
            
            return records
            
        except Exception as e:
            print(f"Error getting recent news: {e}")
            return []
        finally:
            session.close()
    
    def get_stats(self) -> dict:
        """
        Get statistics about the vector database
        
        Returns:
            Dictionary with database statistics
        """
        if not self.is_loaded:
            return {"error": "Vector search engine not loaded"}
        
        session = get_db_session()
        
        try:
            total_records = session.query(NewsFaiss).count()
            
            # Get date range
            first_record = session.query(NewsFaiss).order_by(NewsFaiss.date_publish.asc()).first()
            last_record = session.query(NewsFaiss).order_by(NewsFaiss.date_publish.desc()).first()
            
            stats = {
                "total_records": total_records,
                "faiss_index_size": self.index.ntotal if self.index else 0,
                "model_name": self.model_name,
                "date_range": {
                    "start": first_record.date_publish.isoformat() if first_record else None,
                    "end": last_record.date_publish.isoformat() if last_record else None
                }
            }
            
            return stats
            
        except Exception as e:
            return {"error": f"Error getting stats: {e}"}
        finally:
            session.close()


# Global instance for easy access
vector_search = VectorSearchEngine()


def initialize_vector_search() -> bool:
    """
    Initialize the global vector search engine
    
    Returns:
        True if initialization successful, False otherwise
    """
    return vector_search.load()


def search_news(query: str, k: int = 10) -> List[Tuple[NewsFaiss, float]]:
    """
    Convenience function for searching news
    
    Args:
        query: Search query
        k: Number of results
        
    Returns:
        List of (NewsFaiss record, similarity_score) tuples
    """
    return vector_search.search(query, k)


def search_by_ticker(ticker: str, k: int = 10) -> List[Tuple[NewsFaiss, float]]:
    """
    Convenience function for searching news by ticker
    
    Args:
        ticker: Stock ticker symbol
        k: Number of results
        
    Returns:
        List of (NewsFaiss record, price_change) tuples
    """
    return vector_search.search_by_ticker(ticker, k) 