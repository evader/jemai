# lt.py - The C&C Backend
    import os, threading, requests
    from flask import Flask, request, send_from_directory
    from flask_socketio import SocketIO
    
    app = Flask(__name__, template_folder='templates')
    socketio = SocketIO(app)

    @app.route('/')
    def index():
        return send_from_directory(app.template_folder, 'index.html')

    @socketio.on('query_rag')
    def handle_rag_query(data):
        sid = request.sid
        query = data.get('query')
        
        def run_query():
            try:
                RAG_API_URL = "http://host.docker.internal:11435/query"
                response = requests.post(RAG_API_URL, json={"query": query})
                response.raise_for_status()
                socketio.emit('rag_response', response.json(), room=sid)
            except Exception as e:
                socketio.emit('rag_response', {"error": str(e)}, room=sid)
        
        socketio.start_background_task(run_query)
        
    if __name__ == '__main__':
        socketio.run(app, host='0.0.0.0', port=5000)