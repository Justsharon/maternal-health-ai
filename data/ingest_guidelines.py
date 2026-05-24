"""
Sentinel — Guidelines Ingestion into ChromaDB

Embeds the guidelines corpus into a persistent ChromaDB collection for
retrieval by the Literature Retriever agent.

Reference: Phase 2 RAG (sentence-transformers + ChromaDB), applied to
attributed clinical guidance.
"""

import chromadb
from chromadb.utils import embedding_functions

from data.guidelines_corpus import get_guidelines


CHROMA_PATH = "chroma_guidelines"
COLLECTION_NAME = "maternal_health_guidelines"


def ingest():
    """Embed and store the guidelines corpus in ChromaDB."""
    guidelines = get_guidelines()
    
    # Persistent client (survives restarts — needed for the demo)
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    # Use the same embedding model as Phase 2
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    
    # Fresh collection each ingest (idempotent)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    
    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embed_fn,
    )
    
    # Build documents — we embed the summary, but store full attribution
    documents = [g["summary"] for g in guidelines]
    metadatas = [
        {
            "source": g["source"],
            "issuing_body": g["issuing_body"],
            "topic_tags": ",".join(g["topic_tags"]),
        }
        for g in guidelines
    ]
    ids = [g["id"] for g in guidelines]
    
    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    
    print(f" Ingested {len(guidelines)} guidelines into '{COLLECTION_NAME}'")
    print(f"   Stored at: {CHROMA_PATH}/")
    
    # Quick retrieval test
    print("\n Test query: 'rising blood pressure during pregnancy'")
    results = collection.query(
        query_texts=["rising blood pressure during pregnancy"],
        n_results=2,
    )
    for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
        print(f"\n  Result {i+1} — {meta['source']}")
        print(f"    {doc[:100]}...")


if __name__ == "__main__":
    ingest()