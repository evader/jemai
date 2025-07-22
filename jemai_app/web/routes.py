import os
import logging
from flask import jsonify, render_template, request
from .. import app, socketio
from ..config import JEMAI_HUB, VERSIONS_DIR, SYSTEM_PROMPT
from ..core.tools import PLUGIN_FUNCS
from ..core.rag import rag_search, rag_add_text
from ..core.ai import call_llm
from ..core.voice import speak, voice_muted
from ..core.self_modification import ingest_codebase
import threading

# Check for web ingestion tools
try:
    import requests
    from bs4 import BeautifulSoup
    HAS_WEB_TOOLS = True
except ImportError:
    HAS_WEB_TOOLS = False

@app.route("/")
def route_main():
    return render_template('index.html')

@app.route("/api/files")
def api_files():
    files = [f for f in os.listdir(JEMAI_HUB) if os.path.isfile(os.path.join(JEMAI_HUB, f))]
    return jsonify(sorted(files))

@app.route("/api/versions")
def api_versions():
    return jsonify(sorted(os.listdir(VERSIONS_DIR), reverse=True))

@app.route("/api/plugins")
def api_plugins():
    return jsonify(list(PLUGIN_FUNCS.keys()))

@app.route("/api/file/<path:fname>")
def api_file(fname):
    fpath = os.path.join(JEMAI_HUB, fname)
    if not os.path.exists(fpath): return jsonify({"code":"[File not found]"})
    try:
        with open(fpath, 'r', encoding='utf-8') as f: code = f.read()
        return jsonify({"code": code})
    except Exception as e: return jsonify({"code": f"[Error reading file: {e}]"})

@app.route("/api/version/<path:fname>")
def api_version(fname):
    fpath = os.path.join(VERSIONS_DIR, fname)
    # This should handle directories now
    if not os.path.exists(fpath): return jsonify({"code":"[Version not found]"})
    try:
        # For simplicity, just list files in the version dir. A better approach would be to zip them.
        version_files = [os.path.join(dp, f) for dp, dn, fn in os.walk(fpath) for f in fn]
        version_files = [os.path.relpath(p, fpath) for p in version_files]
        return jsonify({"code": f"Version snapshot contains:\n\n" + "\n".join(version_files)})
    except Exception as e: return jsonify({"code": f"[Error reading version: {e}]"})

@app.route("/api/rag/add_url", methods=['POST'])
def api_rag_add_url():
    if not HAS_WEB_TOOLS:
        return jsonify({"success": False, "message": "requests or beautifulsoup4 not installed."}), 500
    
    url = request.json.get('url')
    if not url:
        return jsonify({"success": False, "message": "URL is required."}), 400

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
        
        text = soup.get_text(separator='\n', strip=True)
        
        if rag_add_text(text, doc_id=f"url_{url}"):
            return jsonify({"success": True, "message": f"Successfully ingested content from {url}"})
        else:
            return jsonify({"success": False, "message": "Failed to add extracted text to RAG."}), 500

    except Exception as e:
        logging.error(f"RAG Ingest URL failed for {url}: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/vscode_chat", methods=['POST'])
def api_vscode_chat():
    data = request.json
    prompt = data.get("prompt", "")
    code = data.get("code", "")

    context = rag_search(prompt)
    user_content = f"CONTEXT:\n{context}\n\nCODE:\n```\n{code}\n```\n\nREQUEST: {prompt}" if context else f"CODE:\n```\n{code}\n```\n\nREQUEST: {prompt}"

    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_content}]
    response_text = call_llm(messages)
    if not voice_muted.is_set():
        threading.Thread(target=speak, args=(response_text,)).start()
    return jsonify({"resp": response_text})

@app.route("/api/voice/status")
def api_voice_status():
    """Returns the current mute status of the voice."""
    return jsonify({"muted": voice_muted.is_set()})

@app.route("/api/voice/toggle", methods=['POST'])
def api_voice_toggle():
    """Toggles the mute status of the voice."""
    if voice_muted.is_set():
        voice_muted.clear()
    else:
        voice_muted.set()
    
    muted_state = voice_muted.is_set()
    logging.info(f"WEB UI: Voice {'muted' if muted_state else 'unmuted'}.")
    # Broadcast the new state to all web clients
    socketio.emit('voice_status_update', {'muted': muted_state})
    return jsonify({"success": True, "muted": muted_state})

@app.route("/api/rag/ingest_codebase", methods=['POST'])
def api_ingest_codebase():
    """Triggers the ingestion of the entire project codebase into the RAG."""
    try:
        # Run in a background thread to not block the server
        threading.Thread(target=ingest_codebase).start()
        return jsonify({"success": True, "message": "Codebase ingestion started in the background."})
    except Exception as e:
        logging.error(f"Failed to start codebase ingestion: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
