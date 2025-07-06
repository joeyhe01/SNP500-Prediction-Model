from sqlalchemy import text
from database import get_db_session
from sentence_transformers import SentenceTransformer

# 1. Load the embedding model (no API key needed)
model = SentenceTransformer("all-MiniLM-L6-v2")

# 2. Create a session
session = get_db_session()

# 3. Sample query text
sample_text = "Earnings report and revenue guidance for Q4 2024"
embedding_vector = model.encode(sample_text).tolist()

# 4. Define the vector similarity query
query = text("""
    SELECT id, accession_number, chunk_id, embedding <-> :embedding AS distance
    FROM sec_filings
    ORDER BY embedding <-> :embedding
    LIMIT 5;
""")

# 5. Execute the query
results = session.execute(query, {"embedding": embedding_vector}).fetchall()

# 6. Show results
for row in results:
    print(dict(row))

# 7. Clean up
session.close()