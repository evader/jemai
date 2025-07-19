import os
    import subprocess
    import threading
    import json
    import time
    import pyperclip
    import psutil
    import sys
    import requests # For calling local synapz_core or other APIs
    
    # --- LangChain & ChromaDB for Local RAG ---
    # These will be needed to query the vector store
    from langchain.embeddings import HuggingFaceEmbeddings
    from langchain.vectorstores import Chroma
    from langchain.schema import Document
    
    # --- Eventlet Monkey Patching (MUST BE EARLY) ---
    try:
        import eventlet
        eventlet.monkey_patch()
    except ImportError:
        print("Eventlet not found, Flask-SocketIO might fall back to a less performant server. Recommended to install eventlet for production.", file=sys.stderr)

    # --- Flask & SocketIO ---
    from flask import Flask, render_template, request, jsonify, send_from_directory
    from flask_socketio import SocketIO