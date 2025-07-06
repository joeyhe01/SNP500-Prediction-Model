from dotenv import load_dotenv
import os
import json
import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer

# Directory containing JSON files
JSON_DIR = 'S:\\Repositories\\vectorDB\\data\\silver'
# Get absolute path to credentials.env one level up from this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, '..', 'credentials.env')
load_dotenv(dotenv_path=env_path)
# Load Sentence Transformer model once
model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding(text):
    """Get embedding vector from Sentence Transformers for given text."""
    embedding = model.encode(text)
    # Convert numpy array to python list for insertion
    return embedding.tolist()

def insert_chunks(conn, chunks):
    """Insert multiple chunks into the sec_filings table."""
    sql = """
    INSERT INTO sec_filings (
        accession_number, chunk_id, text, company_name,
        filing_date, form_type, cik, source_file,
        metadata_json, embedding
    )
    VALUES %s
    ON CONFLICT ON CONSTRAINT uix_accession_chunk DO NOTHING
    """
    records = []
    for chunk in chunks:
        embedding = chunk['embedding']
        # Ensure metadata_json is either a JSON string or None
        metadata = chunk.get('metadata_json')
        if metadata is not None and not isinstance(metadata, str):
            metadata = json.dumps(metadata)
        records.append((
            chunk['accession_number'],
            chunk['chunk_id'],
            chunk['text'],
            chunk.get('company_name'),
            chunk.get('filing_date'),
            chunk.get('form_type'),
            chunk.get('cik'),
            chunk.get('source_file'),
            metadata,
            embedding
        ))

    with conn.cursor() as cur:
        execute_values(cur, sql, records, template=None, page_size=100)
    conn.commit()

def main():
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB")
    )
    
    try:
        for filename in os.listdir(JSON_DIR):
            if not filename.endswith('.json'):
                continue
            filepath = os.path.join(JSON_DIR, filename)
            print(f"Processing {filepath} ...")

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)  # Expecting a list of chunks
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
                continue

            chunks_to_insert = []
            for chunk in data:
                text = chunk.get('text', '')
                if not text:
                    print(f"Skipping chunk with empty text in {filepath}")
                    continue
                try:
                    embedding = get_embedding(text)
                except Exception as e:
                    print(f"Error embedding text in chunk {chunk.get('chunk_id')}: {e}")
                    continue

                chunk_with_embedding = chunk.copy()
                chunk_with_embedding['embedding'] = embedding
                chunks_to_insert.append(chunk_with_embedding)

            if chunks_to_insert:
                print(f"Inserting {len(chunks_to_insert)} chunks into DB...")
                try:
                    insert_chunks(conn, chunks_to_insert)
                    print("Insert successful.")
                except Exception as e:
                    print(f"Error inserting chunks from {filepath}: {e}")
            else:
                print(f"No valid chunks to insert from {filepath}.")

    finally:
        conn.close()

if __name__ == '__main__':
    main()