import os
import psycopg2
from sentence_transformers import SentenceTransformer
import numpy as np

# Load your model (you can pick other models too)
model = SentenceTransformer('all-MiniLM-L6-v2')  # small, fast, good quality embeddings

conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST"),
    port=os.getenv("POSTGRES_PORT"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
    dbname=os.getenv("POSTGRES_DB")
)
cur = conn.cursor()

# Fetch rows that don't have embeddings yet
cur.execute("SELECT chunk_id, text FROM sec_filings WHERE embedding IS NULL OR embedding = '{}'::vector")
rows = cur.fetchall()

for chunk_id, text in rows:
    # Generate embedding using sentence-transformers
    embedding = model.encode(text)

    # Convert numpy array to Postgres vector string format
    embedding_str = '[' + ','.join(map(str, embedding.tolist())) + ']'

    # Update the embedding column for the row
    cur.execute(
        "UPDATE SECFilings SET embedding = %s WHERE chunk_id = %s",
        (embedding_str, chunk_id)
    )

conn.commit()
cur.close()
conn.close()
print("All embeddings generated and stored!")