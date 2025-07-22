import threading
import logging
from jemai_app.__init__ import app, socketio
from jemai_app.config import JEMAI_PORT, FLASK_DEBUG
from jemai_app.main import initialize_app
from jemai_app.core.back_of_house import start_watcher
from jemai_app.desktop.clipboard import clipboard_watcher
from jemai_app.desktop.tray import create_tray_icon  # Or trayold if you want the old one
from jemai_app.core.auto_push import start_auto_git_push  # <-- Auto GitHub push

# Set up logging to show in console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

def run_server():
    """Function to run the Flask-SocketIO server."""
    logger.info(f"Starting Mission Control server on http://localhost:{JEMAI_PORT}")
    socketio.run(app, host='0.0.0.0', port=JEMAI_PORT, debug=FLASK_DEBUG, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    # App initialization (ingest codebase, load mission brief, etc.)
    initialize_app()

    # --- Start all background processes as daemon threads ---
    threading.Thread(target=start_watcher, daemon=True, name="BackOfHouseWatcher").start()
    threading.Thread(target=clipboard_watcher, daemon=True, name="ClipboardWatcher").start()
    start_auto_git_push()  # <-- Start auto GitHub push timer

    # Start the Flask-SocketIO server in its own thread
    server_thread = threading.Thread(target=run_server, daemon=True, name="WebServer")
    server_thread.start()

    logger.info("All background threads started. Starting system tray icon.")

    # Start the system tray icon (blocking call)
    create_tray_icon()
