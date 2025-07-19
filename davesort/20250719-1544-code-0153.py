import os, sys, threading, json, logging
from datetime import datetime
import docker
from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO
from pytz import timezone
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# --- Logging Setup ---
PERTH_TZ = timezone('Australia/Perth')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - Synapz - %(levelname)s - %(message)s', datefmt='%d/%m/%y %H:%M:%S')
logging.Formatter.converter = lambda *args: datetime.now(PERTH_TZ).timetuple()
logger = logging.getLogger(__name__)

# --- App & Globals ---
app = Flask(__name__, static_folder='static', template_folder='templates')
socketio = SocketIO(app) # Don't need eventlet here if using the run command
docker_client = docker.from_env()

# --- RAG Initialization (On-Demand) ---
qa_chain = None
rag_lock = threading.Lock() # Prevents multiple threads from initializing at once

def initialize_rag():
    global qa_chain
    # This function will now be called safely in the background
    with rag_lock:
        # If another thread already finished initializing, just exit.
        if qa_chain is not None and qa_chain != "INIT_FAILED":
            return

        logger.info("🧠 Initializing Synapz RAG Brain (this happens once)...")
        CHROMA_DIR = "./rag/chroma_data"
        if not os.path.isdir(CHROMA_DIR):
            logger.error(f"RAG DB NOT FOUND AT {CHROMA_DIR}. RAG is offline.")
            qa_chain = "INIT_FAILED"
            return
        
        try:
            embedder = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5", model_kwargs={'device': 'cuda'})
            db = Chroma(persist_directory=CHROMA_DIR, embedding_function=embedder)
            retriever = db.as_retriever(search_kwargs={"k": 5})
            llm = Ollama(model="mistral:7b")
            template = "Context: {context}\n\nQuestion: {question}\n\nAnswer: "
            QA_CHAIN_PROMPT = PromptTemplate.from_template(template)
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm, chain_type="stuff", retriever=retriever, chain_type_kwargs={"prompt": QA_CHAIN_PROMPT}
            )
            logger.info("✅ Synapz RAG Brain is Online and Ready.")
        except Exception as e:
            logger.error(f"❌ FAILED TO INITIALIZE RAG BRAIN: {e}", exc_info=True)
            qa_chain = "INIT_FAILED"

# --- API & Sockets ---
@app.route('/')
def index():
    return send_from_directory(app.template_folder, 'index.html')

@socketio.on('query_rag')
def handle_rag_query(data):
    sid = request.sid
    query = data.get('query')
    
    # Check if the RAG is initialized. If not, start the process.
    if qa_chain is None:
        socketio.emit('rag_response', {"response": "Synapz brain is waking up for the first time... this might take a moment."}, room=sid)
        # Run initialization in a background task so it doesn't block this request
        socketio.start_background_task(target=initialize_rag)
        # Give it a moment to start up, a better way would be a loop with a timeout
        time.sleep(10) # Simple wait for initialization to likely complete
    
    if qa_chain == "INIT_FAILED":
        socketio.emit('rag_response', {"error": "RAG system failed to initialize. Check server logs."}, room=sid)
        return
    
    def run_query():
        try:
            # Check again in case it was initializing
            while qa_chain is None:
                time.sleep(1) # Wait for initialization
            
            if qa_chain == "INIT_FAILED":
                socketio.emit('rag_response', {"error": "RAG system failed to initialize on query. Check server logs."}, room=sid)
                return

            result = qa_chain.run(query) 
            socketio.emit('rag_response', {"response": result}, room=sid)
        except Exception as e:
            socketio.emit('rag_response', {"error": f"RAG query error: {str(e)}"}, room=sid)
    
    socketio.start_background_task(run_query)

# ... (other socketio handlers for docker_agent etc. would go here) ...

if __name__ == '__main__':
    logger.info("--- Starting JEM AI Unified Core ---")
    
    # We remove the explicit debug mode from here and let the Dockerfile/docker-compose handle it
    # This allows for a clean production start vs. a debug start.
    # The 'command' in docker-compose will enable debug mode.
    # For production, you would change that command.
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)