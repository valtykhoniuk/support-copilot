from pathlib import Path
from dotenv import load_dotenv
import chromadb
import re
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

load_dotenv()

CHROMA_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "foxscool_kb"

DATA_DIR = Path(__file__).parent / "data" / "kb"

CHUNK_SIZE = 600
CHUNK_OVERLAP = 100
MAX_SECTION_CHARS = 800  

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
    sections = re.split(r"(?=^## )", text, flags=re.MULTILINE)
    sections = [s.strip() for s in sections if s.strip()]
    chunks = []
    for section in sections:
        chunks.extend(_chunk_section(section))
    return chunks


def _chunk_section(section: str) -> list[str]:
    if len(section) <= MAX_SECTION_CHARS:
        return [section]

    subsections = re.split(r"(?=^### )", section, flags=re.MULTILINE)
    subsections = [s.strip() for s in subsections if s.strip()]
    if len(subsections) > 1:
        chunks = []
        for sub in subsections:
            if len(sub) <= MAX_SECTION_CHARS:
                chunks.append(sub)
            else:
                chunks.extend(_fixed_size_chunks(sub, CHUNK_SIZE, CHUNK_OVERLAP))
        return chunks

    return _fixed_size_chunks(section, CHUNK_SIZE, CHUNK_OVERLAP)

def _fixed_size_chunks(text: str, size: int, overlap: int) -> list[str]:
    start = 0
    out = []
    while start < len(text):
        out.append(text[start : start + size])
        start += size - overlap
    return out

def load_md(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def load_all_documents() -> list[dict]:
    docs = []
    for path in DATA_DIR.rglob("*.md"):
        text = load_md(path)
        source = str(path.relative_to(Path(__file__).parent))
        docs.append({"text": text, "source": source})
    return docs

if __name__ == "__main__":
    ingest()
