#!/bin/bash
set -e

echo "🔧 Installing backend Python dependencies..."
#python3 -m venv venv
python -m venv venv
#source venv/bin/activate
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
  source venv/Scripts/activate
else
  source venv/bin/activate
fi
python -m pip install --upgrade pip
#pip install --upgrade pip
pip install -r requirements.txt

echo "📁 Installing frontend npm dependencies and building static files..."
cd frontend
npm install
npm run build
cd ..

echo "✅ Setup complete! All dependencies installed and frontend built."

echo "To create a postgres container with pgvector extension run the following: 
  docker run \
  --name sec_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=trading_data \
  -p 5432:5432 \
  -d ankane/pgvector:latest
  "
  
echo "To start an already existing docker run: docker start sec_db (or your container name)"

echo "Activate the Postgres shell:
docker exec -it $(docker ps -qf ancestor=ankane/pgvector:latest) psql -U postgres -d trading_data
"

echo "Then create the pgvector extension: CREATE EXTENSION IF NOT EXISTS vector;"

echo "Check extension was created: \dx"

echo "Exit shell: \q"

echo "Make sure to export AWS credentials to access S3 bucket
export AWS_ACCESS_KEY_ID=your_access_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_access_key
" 