from flask_socketio import emit
from .. import socketio
import logging

# --- IN-MEMORY, demo data structures. Replace with real data source if needed ---
chat_history = []
tasks = ["Check mission_brief.md", "Scan for directives", "Upgrade UI"]
logs = ["[OK] JemAI started", "[INFO] Clipboard watcher ready"]
directives = ["Restart server", "Ingest new plugin"]

@socketio.on('user_message')
def handle_user_message(data):
    msg = data.get('message', '').strip()
    logging.info(f"[CHAT] User: {msg}")
    if not msg:
        return
    # Dummy reply logic: Replace with actual AI agent code
    reply = f"(JEMAI here) I received: {msg}"
    chat_history.append(('user', msg))
    chat_history.append(('jem', reply))
    emit('jemai_reply', {'reply': reply})

@socketio.on('request_tasks')
def send_tasks():
    emit('update_tasks', {'tasks': tasks})

@socketio.on('request_logs')
def send_logs():
    emit('update_logs', {'logs': logs})

@socketio.on('request_directives')
def send_directives():
    emit('update_directives', {'directives': directives})

@socketio.on('stop_all')
def stop_all():
    logs.append("[WARN] STOP ALL triggered by user.")
    emit('update_logs', {'logs': logs}, broadcast=True)
    # Add real stop logic here if needed
