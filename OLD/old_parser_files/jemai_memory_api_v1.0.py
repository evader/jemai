# jemai_memory_api_v1.0.py
# JEMAI OS Memory API — Version 1.0
# Last Updated: 2025-07-18
# Built by: [AgentName] (pending) for David Lee
"""
FastAPI service for memory search, get, and write.
Serves as the main brain/memory backend for overlay, listeners, and any agent.
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import sqlite3
import hashlib
import json
from typing import List, Optional

app = FastAPI(
    title="JEMAI Memory API",
    description="Core local memory backend for JEMAI OS. Version 1.0",
    version="1.0"
)

# ====== AUTH CONFIG ======
API_USER = "super"
API_PASS = "TechnoAPI69"
security = HTTPBasic()

def verify_auth(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username == API_USER and credentials.password == API_PASS:
        return True
    raise HTTPException(status_code=401, detail="Unauthorized")

# ====== DB CONFIG ======
DB_PATH = "jemai_hub.sqlite3"

def get_conn():
    return sqlite3.connect(DB_PATH)

def search_db(query: str, limit: int = 5):
    conn = get_conn()
    cur = conn.cursor()
    try:
        # Try to match in text, title, or source fields
        cur.execute("""
            SELECT title, text, source FROM memory
            WHERE text LIKE ? OR title LIKE ? OR source LIKE ?
            ORDER BY id DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
        rows = cur.fetchall()
        results = [{"title": r[0], "text": r[1], "source": r[2]} for r in rows]
        return results
    finally:
        conn.close()

def get_by_id(idx: int):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, title, text, source FROM memory WHERE id = ?", (idx,))
        row = cur.fetchone()
        if row:
            return {"id": row[0], "title": row[1], "text": row[2], "source": row[3]}
        return None
    finally:
        conn.close()

def add_entry(title: str, text: str, source: str = "manual"):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO memory (title, text, source) VALUES (?, ?, ?)",
            (title, text, source)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

# ====== ROUTES ======

@app.get("/search", dependencies=[Depends(verify_auth)])
def search(q: str = Query(...), limit: int = 5):
    results = search_db(q, limit=limit)
    return {"results": results, "count": len(results)}

@app.get("/get", dependencies=[Depends(verify_auth)])
def get(idx: int = Query(...)):
    entry = get_by_id(idx)
    if entry:
        return entry
    raise HTTPException(status_code=404, detail="Not found")

@app.post("/add", dependencies=[Depends(verify_auth)])
def add(data: dict):
    title = data.get("title") or "[untitled]"
    text = data.get("text") or ""
    source = data.get("source") or "manual"
    idx = add_entry(title, text, source)
    return {"status": "ok", "id": idx}

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0"}

# Optionally, add a manifest endpoint for agent onboarding:
@app.get("/manifest")
def manifest():
    return {
        "api": "JEMAI Memory API",
        "version": "1.0",
        "endpoints": ["/search", "/get", "/add", "/health", "/manifest"],
        "db": DB_PATH,
        "auth_user": API_USER
    }

# ====== INITIALIZE DB (run only if DB not initialized) ======
def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            text TEXT,
            source TEXT
        )
    """)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    import uvicorn
    uvicorn.run("jemai_memory_api_v1.0:app", host="0.0.0.0", port=8089, reload=True)
