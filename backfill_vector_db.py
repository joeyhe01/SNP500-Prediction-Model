#!/usr/bin/env python3
"""
FAISS Vector Database Backfill Script

This script processes financial news data from 2017-2023, creates embeddings
for title+description, calculates ticker price changes, and stores everything
in a FAISS vector database that can be saved and loaded.
"""

import json
import os
import pickle
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Tuple
import faiss
from sentence_transformers import SentenceTransformer
from models.database import get_db_session, NewsFaiss
from sqlalchemy.orm import Session


class VectorDatabase:
    """FAISS Vector Database manager"""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', dimension: int = 384):
        """
        Initialize the vector database
        
        Args:
            model_name: Sentence transformer model to use for embeddings
            dimension: Dimension of the embedding vectors
        """
        self.model_name = model_name
        self.dimension = dimension
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.id_mapping = {}  # Maps FAISS index to database IDs
        self.next_faiss_id = 0
        
        # Initialize FAISS index (using HNSW for better search performance)
        self.index = faiss.IndexHNSWFlat(dimension, 32)
        self.index.hnsw.efConstruction = 200
        self.index.hnsw.efSearch = 128
        
    def add_embeddings(self, texts: List[str], db_ids: List[int]) -> List[int]:
        """
        Add embeddings to the FAISS index
        
        Args:
            texts: List of texts to embed
            db_ids: Corresponding database IDs
            
        Returns:
            List of FAISS IDs assigned to the embeddings
        """
        if not texts:
            return []
            
        # Generate embeddings
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        embeddings = embeddings.astype('float32')
        
        # Add to FAISS index
        faiss_ids = []
        for i, (embedding, db_id) in enumerate(zip(embeddings, db_ids)):
            faiss_id = self.next_faiss_id
            self.index.add(np.array([embedding]))
            self.id_mapping[faiss_id] = db_id
            faiss_ids.append(faiss_id)
            self.next_faiss_id += 1
            
        return faiss_ids
    
    def save(self, index_path: str = 'faiss_index.bin', mapping_path: str = 'faiss_mapping.pkl'):
        """Save the FAISS index and ID mapping to disk"""
        faiss.write_index(self.index, index_path)
        
        with open(mapping_path, 'wb') as f:
            pickle.dump({
                'id_mapping': self.id_mapping,
                'next_faiss_id': self.next_faiss_id,
                'model_name': self.model_name,
                'dimension': self.dimension
            }, f)
        
        print(f"FAISS index saved to {index_path}")
        print(f"ID mapping saved to {mapping_path}")
    
    def load(self, index_path: str = 'faiss_index.bin', mapping_path: str = 'faiss_mapping.pkl'):
        """Load the FAISS index and ID mapping from disk"""
        if not os.path.exists(index_path) or not os.path.exists(mapping_path):
            print(f"FAISS files not found. Starting with empty index.")
            return False
            
        self.index = faiss.read_index(index_path)
        
        with open(mapping_path, 'rb') as f:
            data = pickle.load(f)
            self.id_mapping = data['id_mapping']
            self.next_faiss_id = data['next_faiss_id']
            
        print(f"FAISS index loaded from {index_path}")
        print(f"Loaded {len(self.id_mapping)} embeddings")
        return True
    
    def search(self, query: str, k: int = 10) -> List[Tuple[int, float]]:
        """
        Search for similar embeddings
        
        Args:
            query: Text query to search for
            k: Number of results to return
            
        Returns:
            List of (database_id, similarity_score) tuples
        """
        if self.index.ntotal == 0:
            return []
            
        query_embedding = self.model.encode([query], normalize_embeddings=True)
        query_embedding = query_embedding.astype('float32')
        
        distances, indices = self.index.search(query_embedding, k)
        
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx in self.id_mapping:
                db_id = self.id_mapping[idx]
                similarity = 1.0 - distance  # Convert distance to similarity
                results.append((db_id, similarity))
                
        return results


def calculate_ticker_price_changes(record: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate price change percentages for mentioned companies
    
    Args:
        record: Financial news record
        
    Returns:
        Dictionary mapping ticker to percentage change (current day to next day)
    """
    ticker_changes = {}
    mentioned_companies = record.get('mentioned_companies', [])
    
    for ticker in mentioned_companies:
        curr_price_key = f'curr_day_price_{ticker}'
        next_price_key = f'next_day_price_{ticker}'
        
        if curr_price_key in record and next_price_key in record:
            curr_price = record[curr_price_key]
            next_price = record[next_price_key]
            
            if curr_price and next_price and curr_price != 0:
                # Calculate percentage change
                pct_change = ((next_price - curr_price) / curr_price) * 100
                ticker_changes[ticker] = round(pct_change, 4)
    
    return ticker_changes


def process_financial_news_file(file_path: str, vector_db: VectorDatabase, session: Session) -> int:
    """
    Process a single financial news file and add to vector database
    
    Args:
        file_path: Path to the JSON file
        vector_db: Vector database instance
        session: Database session
        
    Returns:
        Number of records processed
    """
    print(f"Processing {file_path}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"  Loaded {len(data)} records from file")
    except Exception as e:
        print(f"  Error loading file: {e}")
        return 0
    
    records_to_add = []
    texts_to_embed = []
    db_ids_for_embedding = []
    skipped_count = 0
    
    for i, record in enumerate(data):
        # Extract required fields - handle None values
        title = record.get('title') or ''
        description = record.get('description') or ''
        date_publish = record.get('date_publish')
        
        # Clean and validate
        title = title.strip() if title else ''
        description = description.strip() if description else ''
        
        if not title or not description or not date_publish:
            skipped_count += 1
            continue
            
        # Progress reporting
        if (i + 1) % 1000 == 0:
            print(f"  Processing record {i + 1}/{len(data)}...")
            
        # Parse date
        try:
            if isinstance(date_publish, str):
                # Handle different date formats
                for date_format in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f']:
                    try:
                        parsed_date = datetime.strptime(date_publish, date_format)
                        break
                    except ValueError:
                        continue
                else:
                    # Try with just the date part if datetime parsing fails
                    parsed_date = datetime.strptime(date_publish.split()[0], '%Y-%m-%d')
            else:
                continue
        except (ValueError, AttributeError, IndexError):
            print(f"Could not parse date: {date_publish}")
            continue
        
        # Calculate ticker price changes
        ticker_metadata = calculate_ticker_price_changes(record)
        
        # Create database record
        news_faiss = NewsFaiss(
            faiss_id=0,  # Will be set after embedding
            date_publish=parsed_date,
            title=title,
            description=description,
            ticker_metadata=ticker_metadata
        )
        
        # Add to session and flush to get the ID
        session.add(news_faiss)
        session.flush()
        
        # Prepare for embedding
        text_to_embed = f"{title} {description}"
        texts_to_embed.append(text_to_embed)
        db_ids_for_embedding.append(news_faiss.id)
        records_to_add.append(news_faiss)
    
    # Generate embeddings and add to FAISS
    if texts_to_embed:
        faiss_ids = vector_db.add_embeddings(texts_to_embed, db_ids_for_embedding)
        
        # Update FAISS IDs in database records
        for news_faiss, faiss_id in zip(records_to_add, faiss_ids):
            news_faiss.faiss_id = faiss_id
    
    # Commit all changes
    session.commit()
    
    print(f"  ✓ Successfully processed {len(records_to_add)} records")
    if skipped_count > 0:
        print(f"  ⚠ Skipped {skipped_count} records (missing title/description/date)")
    return len(records_to_add)


def backfill_vector_database():
    """Main function to backfill the vector database from all financial news files"""
    print("Starting FAISS vector database backfill...")
    
    # Initialize vector database
    vector_db = VectorDatabase()
    
    # Try to load existing index
    vector_db.load()
    
    # Get database session
    session = get_db_session()
    
    # Check if we already have data
    existing_count = session.query(NewsFaiss).count()
    if existing_count > 0:
        print(f"Found {existing_count} existing records in database.")
        response = input("Do you want to clear existing data and rebuild? (y/N): ")
        if response.lower() == 'y':
            session.query(NewsFaiss).delete()
            session.commit()
            # Reset vector database
            vector_db = VectorDatabase()
            print("Cleared existing data.")
        else:
            print("Keeping existing data and appending new records.")
    
    # Process all financial news files
    data_dir = 'financial-news-dataset/data'
    total_processed = 0
    
    # Get all JSON files and sort them by year
    json_files = [f for f in os.listdir(data_dir) if f.endswith('_processed.json')]
    json_files.sort()
    
    for filename in json_files:
        file_path = os.path.join(data_dir, filename)
        try:
            count = process_financial_news_file(file_path, vector_db, session)
            total_processed += count
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue
    
    # Save the vector database
    vector_db.save()
    
    session.close()
    
    print(f"\nBackfill complete!")
    print(f"Total records processed: {total_processed}")
    print(f"FAISS index size: {vector_db.index.ntotal}")
    print(f"Vector database saved to disk.")


if __name__ == "__main__":
    backfill_vector_database()
