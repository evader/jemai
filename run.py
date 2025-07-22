import threading
import logging
from jemai_app import app, socketio
from jemai_app.config import JEMAI_PORT, FLASK_DEBUG
from jemai_app.core.main import main_loop
from jemai_app.core.back_of_house import back_of_house_loop
from jemai_app.desktop.clipboard import clipboard_watcher
from jemai_app.desktop.tray import create_tray_icon

# Get the root logger
logger = logging.getLogger()

def run_server():
    """Function to run the Flask-SocketIO server."""
    logger.info(f"Starting Mission Control server on http://localhost:{JEMAI_PORT}")
    # Use allow_unsafe_werkzeug=True for development server in a thread
    socketio.run(app, host='0.0.0.0', port=JEMAI_PORT, debug=FLASK_DEBUG, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    # --- Start all background processes as daemon threads ---
    # Daemon threads will exit when the main program (tray icon) exits.
    
    # Start core application loops
    threading.Thread(target=main_loop, daemon=True, name="MainLoop").start()
    threading.Thread(target=back_of_house_loop, daemon=True, name="BackOfHouseLoop").start()
    
    # Start desktop integration loops
    threading.Thread(target=clipboard_watcher, daemon=True, name="ClipboardWatcher").start()
    
    # Start the Flask-SocketIO server in its own thread
    server_thread = threading.Thread(target=run_server, daemon=True, name="WebServer")
    server_thread.start()
    
    logger.info("All background threads started. Starting system tray icon.")
    
    # --- Start the system tray icon in the main thread ---
    # This is a blocking call and must be the last thing to run.
    # The application will exit when the tray icon is closed.
    create_tray_icon()