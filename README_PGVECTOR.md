Open docker desktop

Start container: 
-   docker start postgres_pgvector

(Optional) Run Postgresql shell: 
-   docker exec -it postgres_pgvector psql -U postgres -d trading_data

Enable pgvector extension:
-   CREATE EXTENSION IF NOT EXISTS vector;

(Optional) check extension was added successfully
-   \dx

Exit shell:
-   \q

Activate virtual environment (venv) in VS Code terminal (Windows 11). Make sure you are
In the root directory:
-   venv\Scripts\Activate

CD into models and run init_database() to initialize tables:
-   cd SNP500-Prediction-Model\models
-   python
-   import database
-   database.init_database()
-   exit() (exit out of python)

Load JSONs into 