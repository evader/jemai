import os
import logging
from .rag import rag_add_text
from ..config import JEMAI_HUB

IGNORE_PATTERNS = ['__pycache__', '.git', 'venv', 'chroma_db', 'versions']

def ingest_codebase():
    logging.info("SELF-AWARENESS: Starting codebase ingestion into RAG.")
    ingested_count = 0
    for root, dirs, files in os.walk(JEMAI_HUB):
        dirs[:] = [d for d in dirs if d not in IGNORE_PATTERNS]
        for file in files:
            if file.endswith(('.py', '.html', '.js', '.css', '.md')):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    relative_path = os.path.relpath(file_path, JEMAI_HUB)
                    doc_id = f"codebase_{relative_path}"
                    rag_add_text(f"--- FILE: {relative_path} ---\n\n{content}", doc_id=doc_id)
                    ingested_count += 1
                except Exception as e:
                    logging.warning(f"Could not ingest file {file_path}: {e}")
    logging.info(f"SELF-AWARENESS: Ingestion complete. Added {ingested_count} files to knowledge base.")
    return ingested_count

def write_file_content(relative_path, content):
    if ".." in relative_path:
        msg = "Security violation: Path traversal detected."
        logging.error(f"SELF-MODIFICATION: {msg}")
        return False, msg
    full_path = os.path.join(JEMAI_HUB, relative_path)
    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        msg = f"Successfully wrote {len(content)} characters to {relative_path}"
        logging.info(f"SELF-MODIFICATION: {msg}")
        return True, msg
    except Exception as e:
        msg = f"Error writing to file {relative_path}: {e}"
        logging.error(f"SELF-MODIFICATION: {msg}")
        return False, msg
