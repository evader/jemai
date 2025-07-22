import os
import time
import logging
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .. import socketio
from ..config import JEMAI_HUB

BOH_PATH = os.path.join(JEMAI_HUB, "backofhouse")
PROCESSED_PATH = os.path.join(BOH_PATH, "processed")


class DirectiveHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        logging.info(f"BACK OF HOUSE: New directive detected: {event.src_path}")
        time.sleep(1)  # Wait for the file to be fully written

        try:
            with open(event.src_path, 'r', encoding='utf-8') as f:
                directive_content = f.read()

            if directive_content.strip():
                logging.info("BACK OF HOUSE: Sending directive to AI Director.")
                socketio.emit('director_message', {'directive': directive_content})

            # Archive the directive file
            shutil.move(event.src_path, PROCESSED_PATH)
            logging.info(f"BACK OF HOUSE: Archived directive file to {PROCESSED_PATH}")

        except Exception as e:
            logging.error(f"BACK OF HOUSE: Error processing directive {event.src_path}: {e}")


def start_watcher():
    os.makedirs(BOH_PATH, exist_ok=True)
    os.makedirs(PROCESSED_PATH, exist_ok=True)

    event_handler = DirectiveHandler()
    observer = Observer()
    observer.schedule(event_handler, BOH_PATH, recursive=False)
    observer.daemon = True
    observer.start()
    logging.info(f"BACK OF HOUSE: Monitoring for new directives in {BOH_PATH}")


def back_of_house_loop():
    start_watcher()
