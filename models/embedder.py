import os, json, boto3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sentence_transformers import SentenceTransformer
from database import Base, SECFilings

# --- AWS S3 CONFIG ---
AWS_BUCKET_NAME = 'datasci-210-summer-2025-sec-documents'
S3_PREFIX = '' 
REGION = 'us-east-1'

# --- DB CONFIG (adjust if needed) ---
DB_USER = 'postgres'
DB_PASS = 'postgres'
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'trading_data'

# --- SQLAlchemy setup ---
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# --- S3 Client setup ---
s3 = boto3.client("s3", region_name=REGION)

# --- Load sentence-transformer model ---
model = SentenceTransformer('all-MiniLM-L6-v2')  # 384-dimensional embeddings

def list_json_files(bucket, prefix=''):
    '''List all JSON files in the specified S3 bucket and prefix.'''
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".json"):
                yield obj["Key"]

def load_json_from_s3(bucket, key):
    '''Load JSON data from an S3 object.'''
    response = s3.get_object(Bucket=bucket, Key=key)
    return json.loads(response["Body"].read().decode("utf-8"))

def process_and_insert_chunks(chunks):
    '''Process each chunk and insert into the database.
    '''
    for chunk in chunks:
        text = chunk.get("text", "")
        vector = model.encode(text).tolist()  # Convert numpy array to list for SQLAlchemy Vector

        record = SECFilings(
            accession_number=chunk.get("accession_number"),
            chunk_id=chunk.get("chunk_id"),
            text=text,
            company_name=chunk.get("company_name"),
            filing_date=chunk.get("filing_date"),
            form_type=chunk.get("form_type"),
            cik=chunk.get("cik"),
            source_file=chunk.get("source_file"),
            metadata_json=chunk,
            embedding=vector
        )
        try:
            session.add(record)
            session.commit()
            print(f"✅ Inserted: {record.accession_number}, chunk {record.chunk_id}")
        except IntegrityError:
            session.rollback()
            print(f"⚠️ Skipped duplicate: {record.accession_number}, chunk {record.chunk_id}")
        except Exception as e:
            session.rollback()
            print(f"❌ Error inserting chunk {chunk.get('chunk_id')}: {e}")

def main():
    print("🚀 Starting ingestion from S3...")
    for key in list_json_files(AWS_BUCKET_NAME, S3_PREFIX):
        print(f"📄 Processing file: {key}")
        try:
            chunks = load_json_from_s3(AWS_BUCKET_NAME, key)
            process_and_insert_chunks(chunks)
        except Exception as e:
            print(f"❌ Failed to process {key}: {e}")

    print("✅ Done.")

if __name__ == "__main__":
    main()