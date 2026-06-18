from pathlib import Path
import chromadb
from dotenv import load_dotenv
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

CHROMA_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "foxscool_kb"
TOP_K = 5

load_dotenv()

def get_collection():
     embed_fn = SentenceTransformerEmbeddingFunction(model_name = "all-MiniLM-L6-v2")
     client = chromadb.PersistentClient(path=str(CHROMA_DIR))
     return client.get_collection(name=COLLECTION_NAME, embedding_function=embed_fn)

def retrieve(query: str, top_k: int = TOP_K) -> list[dict]:
    collection = get_collection()
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    hits = []
    for text, metadata, distance in zip(documents, metadatas, distances):
        hits.append({
            "text": text,
            "source": metadata["source"],
            "distance": distance,
        })

    return hits

if __name__ == "__main__":
    q = "How much does the Beginner plan cost?"
    hits = retrieve(q)
    for i, hit in enumerate(hits):
        print(f"\n=== Hit {i+1} (distance: {hit['distance']:.3f}) ===")
        print(f"Source: {hit['source']}")
        print(hit["text"][:300])