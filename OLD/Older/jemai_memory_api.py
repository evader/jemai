import os
import sqlite3
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import List
import secrets

API_PASSWORD = "TechnoAPI69"  # FINAL password, no placeholders

DATA_DIR = r"C:\JEMAI_HUB"
SQLITE_PATH = os.path.join(DATA_DIR, "jemai_hub.sqlite3")

app = FastAPI(title="JEMAI Memory API")
security = HTTPBasic()

def check_auth(credentials: HTTPBasicCredentials = Depends(security)):
    correct_password = secrets.compare_digest(credentials.password, API_PASSWORD)
    if not correct_password:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/")
def root():
    return {"msg": "JEMAI Memory API ready"}

@app.get("/search", dependencies=[Depends(check_auth)])
def search(q: str, limit: int = 5):
    """
    Search memory DB for any chunk containing the keyword/phrase (case-insensitive).
    """
    conn = sqlite3.connect(SQLITE_PATH)
    c = conn.cursor()
    q_clean = f"%{q.lower()}%"
    c.execute("SELECT hash, source, title, text, date FROM chunks WHERE LOWER(text) LIKE ? LIMIT ?", (q_clean, limit))
    rows = c.fetchall()
    conn.close()
    results = [{"hash": row[0], "source": row[1], "title": row[2], "text": row[3], "date": row[4]} for row in rows]
    return {"results": results}

@app.get("/get", dependencies=[Depends(check_auth)])
def get_chunk(hash: str):
    """
    Retrieve a chunk by its SHA256 hash.
    """
    conn = sqlite3.connect(SQLITE_PATH)
    c = conn.cursor()
    c.execute("SELECT hash, source, title, text, date, meta FROM chunks WHERE hash = ?", (hash,))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return {"hash": row[0], "source": row[1], "title": row[2], "text": row[3], "date": row[4], "meta": row[5]}

@app.exception_handler(Exception)
def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error": str(exc)})

# ----
# To run: uvicorn jemai_memory_api:app --reload --host 0.0.0.0 --port 8089
# ----
