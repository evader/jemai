import os
import subprocess
import threading
import json
import time
import psutil
import sys
import docker
import requests

# --- CRITICAL: Eventlet monkey patching MUST happen at the very top ---
try:
    import eventlet
    eventlet.monkey_patch()
except ImportError:
    print("Eventlet not found, using Flask's default development server.", file=sys.stderr)

from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO
from langchain_community.embeddings import HuggingFaceEmbeddings # Updated Import
from langchain_community.vectorstores import Chroma # Updated Import
from langchain_community.llms import Ollama # Updated Import
from langchain.chains import RetrievalQA

# --- App & Global Initializations ---
app = Flask(__name__, static_folder='static', template_folder='templates')
socketio = SocketIO(app, async_mode='eventlet')
docker_client = docker.from_env()

# --- RAG Initialization (On-Demand) ---
# We will initialize these lazily, inside a thread, to avoid startup conflicts.
qa_chain = None
rag_lock = threading.Lock() # A lock to prevent multiple initializations at once

def initialize_rag():
    global qa_chain
    # This function will now be called in the background
    with rag_lock:
        if qa_chain is not None:
            # Already initialized by another thread
            return

        print("🧠 LAZY-LOADING RAG BRAIN: This will happen only once...")
        try:
            CHROMA_DIR = "./rag/chroma_data"
            EMBED_MODEL = "BAAI/bge-small-en-v1.5"
            OLLAMA_MODEL = "mistral:7b" 

            if not os.path.exists(CHROMA_DIR):
                print(f"❌ RAG DATABASE NOT FOUND AT {CHROMA_DIR}. RAG features will be disabled.", file=sys.stderr)
                qa_chain = "INITIALIZATION_FAILED"
                return

            embedder = HuggingFaceEmbeddings(model_name=EMBED_MODEL, model_kwargs={'device': 'cuda'})
            db = Chroma(persist_directory=CHROMA_DIR, embedding_function=embedder)
            retriever = db.as_retriever(search_kwargs={"k": 5})
            llm = Ollama(model=OLLAMA_MODEL)
            
            # Creating a System Prompt Template
            from langchain.prompts import PromptTemplate
            template = """
            Use the following pieces of context from our shared history to answer the user's question.
            If you don't know the answer from the context, just say that you don't have that information in your memory, don't try to make up an answer.
            Be direct, concise, and embody the Synapz persona.
            
            Context: {context}
            
            Question: {question}
            
            Helpful Answer:"""
            QA_CHAIN_PROMPT = PromptTemplate.from_template(template)

            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=False,
                chain_type_kwargs={"prompt": QA_CHAIN_PROMPT} # Injecting the prompt
            )
            print("✅ Synapz RAG Brain is Online and Ready.")
        except Exception as e:
            print(f"❌ FAILED TO INITIALIZE RAG BRAIN: {e}", file=sys.stderr)
            qa_chain = "INITIALIZATION_FAILED"


# --- Docker Agent Functions ---
def list_containers():
    try:
        return [{ "name": c.name, "status": c.status } for c in docker_client.containers.list(all=True)]
    except Exception as e:
        return f"Error listing containers: {str(e)}"

# --- Flask & SocketIO Endpoints ---
@app.route('/')
def index():
    return send_from_directory(app.template_folder, 'index.html')

@socketio.on('query_rag')
def handle_rag_query(data):
    sid = request.sid
    query = data.get('query')

    #
    # THIS IS THE KEY FIX: Initialize RAG on the first query.
    #
    if qa_chain is None:
        # Start initialization in a background thread so it doesn't block the server
        socketio.emit('rag_response', {"response": "Synapz brain is waking up for the first time... this might take a moment."}, room=sid)
        init_thread = threading.Thread(target=initialize_rag)
        init_thread.start()
        init_thread.join() # Wait for initialization to complete on this first call
    
    if qa_chain == "INITIALIZATION_FAILED":
        socketio.emit('rag_response', {"error": "RAG system failed to initialize. Check server logs."}, room=sid)
        return
    
    def run_query():
        try:
            # The qa_chain.run() method is simpler and just returns the string.
            # For more complex chains, you might use qa_chain.invoke(query)
            result = qa_chain.run(query) 
            socketio.emit('rag_response', {"response": result}, room=sid)
        except Exception as e:
            socketio.emit('rag_response', {"error": f"Error during RAG query: {str(e)}"}, room=sid)
    
    socketio.start_background_task(run_query)

@socketio.on('docker_agent')
def handle_docker_command(data):
    sid = request.sid
    command = data.get('command')
    response = {"status": "error", "data": "Invalid Docker command"}
    if command == 'list':
        response = {"status": "ok", "data": list_containers()}
    socketio.emit('docker_response', response, room=sid)

if __name__ == '__main__':
    print("--- Starting JEM AI Unified Core Web Server on port 5000 ---")
    socketio.run(app, host='0.0.0.0', port=5000)