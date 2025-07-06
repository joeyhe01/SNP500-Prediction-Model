import os
import json
from sqlalchemy.exc import SQLAlchemyError
from sentence_transformers import SentenceTransformer
from database import SECFilings, get_db_session

# Load the embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')  # Small & fast model

def insert_sec_filings_with_embeddings(directory_path: str):
    session = get_db_session()

    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            file_path = os.path.join(directory_path, filename)
            print(f"📄 Processing file: {file_path}")

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    chunks = json.load(f)

                for chunk in chunks:
                    text = chunk.get("text", "")
                    if not text.strip():
                        continue
                    
                    # Generate vector embedding
                    embedding = model.encode(text).tolist()

                    filing = SECFilings(
                        accession_number=chunk.get("accession_number"),
                        chunk_id=chunk.get("chunk_id"),
                        text=text,
                        company_name=chunk.get("company_name"),
                        filing_date=chunk.get("filing_date"),
                        form_type=chunk.get("form_type"),
                        cik=chunk.get("cik"),
                        source_file=chunk.get("source_file"),
                        metadata_json=chunk.get("metadata_json", None),
                        embedding=embedding  # Vector column
                    )
                    session.add(filing)

                session.commit()
                print(f"✅ Inserted and embedded {filename}")

            except (json.JSONDecodeError, SQLAlchemyError) as e:
                session.rollback()
                print(f"❌ Error processing {filename}: {e}")

    session.close()

if __name__ == "__main__":
    directory = 'S:\\Repositories\\vectorDB\\data\\silver'
    insert_sec_filings_with_embeddings(directory)