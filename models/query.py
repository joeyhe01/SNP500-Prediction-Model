from sentence_transformers import SentenceTransformer

#sample query
model = SentenceTransformer('all-MiniLM-L6-v2')
query_text = "tesla is doing poorly in 2025"
query_embedding = model.encode(query_text).tolist()
print(query_embedding)  # copy this output vector into the SQL query below