import time
import logging
import pyperclip
from ..core.tools import run_command
from ..core.voice import speak
from ..config import TRIGGER_PREFIX

def clipboard_watcher():
    recent_val = ""
    logging.info("CLIPBOARD: Watcher thread started.")
    while True:
        try:
            val = pyperclip.paste()
            if val != recent_val and val.strip().lower().startswith(TRIGGER_PREFIX):
                command = val.strip()[len(TRIGGER_PREFIX):].strip()
                logging.info(f"CLIPBOARD: Trigger detected! Command: '{command}'")
                output = run_command(command)
                pyperclip.copy(output)
                speak(f"Command executed. Output is in your clipboard.")
                recent_val = output
            else:
                recent_val = val
        except Exception:
            pass # Suppress errors from pyperclip when clipboard is busy
        time.sleep(1.0)
