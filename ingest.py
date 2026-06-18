from pathlib import Path
from dotenv import load_dotenv
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

load_dotenv()

CHROMA_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "foxscool_kb"

DATA_DIR = Path(__file__).parent / "data" / "kb"

CHUNK_SIZE = 600
CHUNK_OVERLAP = 100

def ingest():
    embed_fn = SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    try:
       client.delete_collection(COLLECTION_NAME) 
    except:
        print('It was first time')

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embed_fn
    )

    docs = load_all_documents()
    all_chunks = []
    all_ids = []
    all_metadatas = []

    for doc in docs:
        chunks = chunk_text(doc["text"])
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_ids.append(f"{doc['source']}::chunk_{i}")
            all_metadatas.append({"source": doc["source"]})

    collection.add(
        documents=all_chunks,
        ids=all_ids,
        metadatas=all_metadatas
    )

    print(f"Ingested {len(all_chunks)} chunks from {len(docs)} files")

def chunk_text(text: str) -> list[str]:
    start = 0
    chunks = []
    while start < len(text):
        chunks.append(text[start : start + CHUNK_SIZE])
        start = start + CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def load_md(path: Path) -> str:
    fileIn = Path(path);
    text = ""
    mdFileIn = open(fileIn, 'r', encoding="utf-8")
    for i in mdFileIn:
        text = text + " " + i
    mdFileIn.close()
    return text

def load_all_documents() -> list[dict]:
    docs = []
    for path in DATA_DIR.rglob("*.md"):
        text = load_md(path)
        source = str(path.relative_to(Path(__file__).parent))
        docs.append({"text": text, "source": source})
    return docs

if __name__ == "__main__":
    ingest()
