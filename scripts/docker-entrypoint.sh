#!/bin/sh
set -e

# ingest once if Chroma volume is empty
if [ ! -d "chroma_db" ] || [ -z "$(ls -A chroma_db 2>/dev/null)" ]; then
  echo "Running ingest (first start)..."
  python ingest.py
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000