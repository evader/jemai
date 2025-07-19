import os
import re
import json
import csv
import hashlib
import sqlite3
from pathlib import Path
import importlib

DATA_DIR = r"C:\JEMAI_HUB"
PLUGINS_DIR = Path(DATA_DIR) / "plugins"
CHUNK_SIZE = 1000
EXPORT_JSONL = True
EXPORT_CSV = True

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PLUGINS_DIR, exist_ok=True)

def hash_text(text):
    clean = re.sub(r'\s+', ' ', text.strip().lower())
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()

def yield_chunks(text, chunk_size=CHUNK_SIZE):
    words = text.split()
    for i in range(0, len(words), chunk_size):
        yield " ".join(words[i:i+chunk_size])

def fallback_parser(filepath):
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        return [{
            "source": "unknown",
            "title": os.path.basename(filepath),
            "text": text,
            "date": "",
            "metadata": {"origin": str(filepath)}
        }]
    except Exception:
        return []

def discover_plugins():
    parsers = []
    for fname in os.listdir(PLUGINS_DIR):
        if fname.endswith(".py") and not fname.startswith("__"):
            mod = importlib.import_module(f"plugins.{fname[:-3]}")
            if hasattr(mod, "register"):
                mod.register(parsers.append)
    return parsers

def load_existing_hashes_sqlite(sqlite_path):
    hashes = set()
    if not os.path.exists(sqlite_path):
        return hashes
    conn = sqlite3.connect(sqlite_path)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS chunks (hash TEXT PRIMARY KEY, source TEXT, title TEXT, text TEXT, date TEXT, meta TEXT)")
    for row in c.execute("SELECT hash FROM chunks"):
        hashes.add(row[0])
    conn.close()
    return hashes

def add_to_sqlite(sqlite_path, chunk):
    conn = sqlite3.connect(sqlite_path)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS chunks (hash TEXT PRIMARY KEY, source TEXT, title TEXT, text TEXT, date TEXT, meta TEXT)")
    c.execute("INSERT OR IGNORE INTO chunks VALUES (?, ?, ?, ?, ?, ?)", (
        chunk['hash'], chunk['source'], chunk['title'], chunk['text'], chunk.get('date', ''), json.dumps(chunk.get('metadata', {}))
    ))
    conn.commit()
    conn.close()

def write_jsonl(jsonl_path, chunk):
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

def write_csv(csv_path, chunk, fieldnames=None):
    exists = os.path.exists(csv_path)
    with open(csv_path, "a", encoding="utf-8", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames or ["hash", "source", "title", "text", "date"])
        if not exists:
            writer.writeheader()
        writer.writerow({k: chunk.get(k, "") for k in writer.fieldnames})

def main():
    # Discover plugins
    import sys
    sys.path.insert(0, str(Path(DATA_DIR)))  # For plugins import
    parsers = discover_plugins()
    print(f"Loaded {len(parsers)} parser plugins.")

    # Find files to process
    files_to_scan = []
    for root, dirs, files in os.walk(DATA_DIR):
        # Skip the output DB/JSONL/CSV and plugins themselves
        if root.startswith(str(PLUGINS_DIR)) or root == DATA_DIR:
            continue
        for f in files:
            path = Path(root) / f
            if "jemai_hub" in path.name:  # skip outputs
                continue
            files_to_scan.append(str(path))

    # Prepare output
    sqlite_path = os.path.join(DATA_DIR, "jemai_hub.sqlite3")
    jsonl_path = os.path.join(DATA_DIR, "jemai_hub.jsonl")
    csv_path = os.path.join(DATA_DIR, "jemai_hub.csv")
    existing_hashes = load_existing_hashes_sqlite(sqlite_path)
    seen = set(existing_hashes)
    n_total = n_unique = n_dupe = 0

    for path in files_to_scan:
        handled = False
        for parser in parsers:
            try:
                results = parser(path)
                if results:
                    handled = True
                    break
            except Exception as e:
                continue
        if not handled:
            results = fallback_parser(path)
        for conv in results:
            for chunk_text in yield_chunks(conv["text"], CHUNK_SIZE):
                chunk_hash = hash_text(chunk_text)
                n_total += 1
                if chunk_hash in seen:
                    n_dupe += 1
                    continue
                seen.add(chunk_hash)
                chunk = {
                    "hash": chunk_hash,
                    "source": conv.get("source", "unknown"),
                    "title": conv.get("title", ""),
                    "text": chunk_text,
                    "date": conv.get("date", ""),
                    "metadata": conv.get("metadata", {})
                }
                add_to_sqlite(sqlite_path, chunk)
                if EXPORT_JSONL:
                    write_jsonl(jsonl_path, chunk)
                if EXPORT_CSV:
                    write_csv(csv_path, chunk)
                n_unique += 1

    print(f"\nALL DONE! {n_total} total chunks scanned, {n_unique} unique chunks imported, {n_dupe} exact duplicates skipped.")
    print(f"Outputs:\n  {sqlite_path}\n  {jsonl_path}\n  {csv_path}\n")
    print("Add new plugins to /plugins, rerun script any time!")

if __name__ == "__main__":
    main()