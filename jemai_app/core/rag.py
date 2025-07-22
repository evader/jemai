import time
import logging
from ..config import CHROMA_PATH

# Check for ChromaDB library during import
try:
    import chromadb
    from chromadb.utils import embedding_functions
    
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    embed_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    RAG_COLLECTION = chroma_client.get_or_create_collection(name="jemai_rag_memory", embedding_function=embed_func)
    HAS_CHROMADB = True
    logging.info("ChromaDB RAG system initialized.")
except ImportError:
    HAS_CHROMADB = False
    RAG_COLLECTION = None
    logging.warning("chromadb or sentence-transformers not found. RAG system disabled.")
except Exception as e:
    HAS_CHROMADB = False
    RAG_COLLECTION = None
    logging.error(f"ChromaDB initialization failed: {e}")


def rag_add_text(text, doc_id=None):
    if not HAS_CHROMADB or not text.strip(): return False
    if not doc_id: doc_id = f"doc_{int(time.time())}_{hash(text)}"
    try:
        RAG_COLLECTION.add(documents=[text], ids=[doc_id])
        logging.info(f"RAG: Added document '{doc_id}'")
        return True
    except Exception as e:
        logging.error(f"RAG: Failed to add document: {e}")
        return False

def rag_search(query, n_results=3):
    if not HAS_CHROMADB or not query.strip(): return ""
    try:
        results = RAG_COLLECTION.query(query_texts=[query], n_results=n_results)
        if not results or not results.get('documents') or not results['documents'][0]:
            return ""
        context = "\n---\n".join(results['documents'][0])
        logging.info(f"RAG: Found context for query '{query[:30]}...'")
        return context
    except Exception as e:
        logging.error(f"RAG: Search failed: {e}")
        return ""
