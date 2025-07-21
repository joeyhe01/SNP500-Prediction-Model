import os
import psycopg2
import numpy as np
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', 'credentials.env'))

# Load model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Query
#query_text = "tesla is doing poorly in 2025"
query_text = "The Texas-based EV leader reported significant losses in the first quarter of 2025, raising concerns about future profitability."
query_embedding = model.encode(query_text).tolist()

# Connect to PostgreSQL
conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=os.getenv("POSTGRES_PORT", 5432),
    user=os.getenv("POSTGRES_USER", "postgres"),
    password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    dbname=os.getenv("POSTGRES_DB", "trading_data")
)

query_embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

with conn.cursor() as cur:
    cur.execute(f"""
        SELECT accession_number, chunk_id, company_name, filing_date, text,
            1 - (embedding <#> '{query_embedding_str}'::vector) AS cosine_similarity
        FROM sec_filings
        WHERE company_name ILIKE '%%tesla%%' OR text ILIKE '%%tesla%%'
        ORDER BY embedding <#> '{query_embedding_str}'::vector
        LIMIT 5;
    """)

    rows = cur.fetchall()
    for row in rows:
        accession_number, chunk_id, company_name, filing_date, text, score = row
        if score is not None:
            print(f"\n--- Match (Score: {score:.4f}) ---")
        else:
            print("\n--- Match (Score: N/A) ---")
        print(f"Company: {company_name}, Filing Date: {filing_date}, Accession: {accession_number}, Chunk: {chunk_id}")
        print(f"Text: {text[:500]}...")
