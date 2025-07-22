import logging
from flask import Flask
from flask_socketio import SocketIO
from .config import TEMPLATES_DIR

# Configure logging for the entire application
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    handlers=[
        logging.FileHandler("jemai.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Initialize Flask and SocketIO
app = Flask(__name__, template_folder=TEMPLATES_DIR)
socketio = SocketIO(app, async_mode="threading")

# Import web routes and socket handlers to register them
from .web import routes, sockets
