import os
import threading
import requests
import logging
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO
from pytz import timezone # For timezone-aware timestamps

# --- LOGGING SETUP ---
# Create a logger that will output to the console with your timezone
PERTH_TZ = timezone('Australia/Perth')
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
# Set the timezone for the logger's formatter
logging.Formatter.converter = lambda *args: datetime.now(PERTH_TZ).timetuple()
logger = logging.getLogger(__name__)

# --- APP SETUP ---
app = Flask(__name__, template_folder='templates')
socketio = SocketIO(app)

# --- ROUTES & SOCKETS ---
@app.route('/')
def index():
    return send_from_directory(app.template_folder, 'index.html')

@socketio.on('query_rag')
def handle_rag_query(data):
    sid = request.sid
    query = data.get('query')
    logger.info(f"Received RAG query from client {sid}: '{query}'")
    
    def run_query():
        try:
            RAG_API_URL = "http://host.docker.internal:11435/query"
            response = requests.post(RAG_API_URL, json={"query": query}, timeout=120)
            response.raise_for_status()
            response_data = response.json()
            socketio.emit('rag_response', response_data, room=sid)
            logger.info(f"Successfully sent RAG response to client {sid}.")
        except Exception as e:
            logger.error(f"Error handling RAG query for client {sid}: {e}")
            socketio.emit('rag_response', {"error": str(e)}, room=sid)
    
    socketio.start_background_task(run_query)

if __name__ == '__main__':
    logger.info("--- Starting JEM AI C&C Backend (lt.py) ---")
    # Using eventlet is preferred for production with SocketIO
    try:
        import eventlet
        eventlet.monkey_patch()
        socketio.run(app, host='0.0.0.0', port=5000)
    except ImportError:
        logger.warning("Eventlet not found, using standard Flask development server.")
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)