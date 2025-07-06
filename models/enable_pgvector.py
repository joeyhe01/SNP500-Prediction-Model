#add the pgvector extension to postgres

import os
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[1] / 'credentials.env'
print(env_path)
load_dotenv(dotenv_path=env_path)
print(os.getenv('POSTGRES_USER'),os.getenv('POSTGRES_PASSWORD'),os.getenv('POSTGRES_HOST'), os.getenv('POSTGRES_PORT'), os.getenv('POSTGRES_DB'))

# Construct database URL from .env variables
db_url = f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@" \
         f"{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"

# Create engine and enable pgvector
engine = create_engine(db_url)

with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    print("✅ pgvector extension enabled.")