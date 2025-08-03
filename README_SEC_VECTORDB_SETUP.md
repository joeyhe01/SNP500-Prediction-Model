# Vector Database Implementation
This document describes how to:
-   Create the `vectordb` database using the `ankane/pgvector` image. This it the official community-maintained Postgres image with pgvector vector extension pre-installed.
-   Connect to an already existing `vectordb`.

## Overview
The `vectordb` is built using a Postgres image with pgvector installed. pgvector allows the Postgres extension to handel embeddings as a table column. This will allow cosine similarity search across the Postgres table.

### First Time Setup
Create a container named `vectordb` using the ankane/pgvector image.
Make sure the `Docker Desktop` app is open and running in the background.
In windows run this in powershell or Git Bash.
```bash
docker run \
  --name vectordb \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=trading_data \
  -p 5432:5432 \
  -d ankane/pgvector:latest
```

Check that the container was properly created and is running
```bash
docker ps -a
```

Activate the `Postgres Shell` by running the following command:
```bash
docker exec -it $(docker ps -qf ancestor=ankane/pgvector:latest) psql -U postgres -d trading_data
```

Activate the 'pgvector' extension using SQL in the Postgres Shell:
```bash
CREATE EXTENSION IF NOT EXISTS vector;
```
This should return CREATE EXTENSION. You can also run `\dx` to check what extensions are enabled in the current database.
To exit the Postgres shell run `\q`. You can also keep the shell running and open a new terminal/bash CLI as we will inspect the database again.

The `models/database.py` is the script responsible for defining and initializing tables and schemas in the trading_data database. Make sure you update this script to contain a table for your data. For the purpose of the JSON/SEC files in this project, here is how the table will be structured:
```bash 
class SECFilings(Base):
    __tablename__ = 'sec_filings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    accession_number = Column(String, nullable=False, index=True)  
    chunk_id = Column(Integer, nullable=False)                     
    text = Column(Text, nullable=False)                            
    company_name = Column(String)
    filing_date = Column(String, index=True)                        
    form_type = Column(String)
    cik = Column(String)
    source_file = Column(String)
    metadata_json = Column(JSON)
    embedding = Column(Vector(384))                                    

    __table_args__ = (
        # Prevent duplicates if multiple ingestions run
        UniqueConstraint('accession_number', 'chunk_id', name='uix_accession_chunk'),
    )

    def __repr__(self):
        return f"<SECFilings(accession={self.accession_number}, chunk_id={self.chunk_id})>" 
```
This will create a table named `sec_filings`.
Then run the following function in `models/database.py` to initialize the newly created table:
```bash
def get_db_session():
    """Create and return a database session. Initializes DB schema only once per process."""
    global _engine, _Session
    if _engine is None:
        _engine = get_engine()
    if _Session is None:
        _Session = sessionmaker(bind=_engine)
    # Ensure DB is initialized only once
    init_database()
    return _Session()

Example run
-   switch directories to the folder containing database.py: cd models
-   activate the Python shell: python
-   import the database.py file into the python shell: import database.py
-   run the function: database.get_db_session()

```

Now enter the Postgres shell again to check if the table was created using `\dt`.

### Subsequen Run
If you have already created the `vectordb` container using ankane/pgvector image and wish to access it just run the following command:
```bash
docker start vectordb
```

### Updating the Tables
Now that the `sec_filings` table has been created, to add data to it run `models/embedder.py`.
This function connects to an S3 bucket containing current SEC documents for top SNP 500 companies. Before running the script make sure you have access to your `IAM AWS` account and have your `access_key_id` and `secret_access_key` ready.
Export them in the terminal in the following manner so the script has access to them when trying to connect to the bucket:
```bash
export AWS_ACCESS_KEY_ID=your_access_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_access_key 
```
Then simply run the following line while in the models directory:
```bash
python embedder.py
```
This will take a few minutes.

***CONGRATULATIONS!*** 
The vector database is now setup and can be queried by running query.py in the models directory.