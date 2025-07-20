import os, re, sys, time, threading, subprocess
import tkinter as tk
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import win32gui, win32con, win32clipboard

# ---- LOGGING ----
def log(msg, color=None):
    codes = {
        "green": "\033[92m", "yellow": "\033[93m", "red": "\033[91m", "cyan": "\033[96m", "reset": "\033[0m"
    }
    if color and sys.stdout.isatty():
        print(f"{codes[color]}{msg}{codes['reset']}")
    else:
        print(msg)

# ---- TRIGGER PATTERNS ----
TRIGGER_PATTERNS = [
    re.compile(r"jemai::run::(.+)", re.IGNORECASE),
    re.compile(r"jemai::exec::(.+)", re.IGNORECASE),
    re.compile(r"jemai::list::(.+)", re.IGNORECASE)
]
POLL_SECONDS = 1.2

# ---- WATCHER ----
def get_foreground_text():
    try:
        hwnd = win32gui.GetForegroundWindow()
        length = win32gui.SendMessage(hwnd, win32con.WM_GETTEXTLENGTH) + 1
        buf = win32gui.PyGetMemory(length, 0)
        win32gui.SendMessage(hwnd, win32con.WM_GETTEXT, length, buf)
        text = str(buf[:-1], errors="ignore")
        if not text.strip():
            try:
                win32clipboard.OpenClipboard()
                text = win32clipboard.GetClipboardData()
                win32clipboard.CloseClipboard()
            except Exception:
                text = ""
        return text
    except Exception as e:
        log(f"[WARN] Foreground text error: {e}", "yellow")
        return ""

def match_command(text):
    for line in text.splitlines():
        for pat in TRIGGER_PATTERNS:
            m = pat.search(line)
            if m:
                return m.group(1).strip()
    return None

class JemaiOverlay(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JEMAI Command Status")
        self.geometry("500x140+100+40")
        self.resizable(False, False)
        self.label = tk.Label(self, text="Status: Idle", font=("Segoe UI", 15), bg="#222", fg="#fff")
        self.label.pack(fill="both", expand=True, padx=14, pady=12)
        self.protocol("WM_DELETE_WINDOW", self.hide)
        self.status = "idle"
        self.cmd = ""
        self.proc = None
        self.after_id = None
        self.configure(bg="#222")
        self.attributes("-topmost", True)
        self.bind("<Escape>", lambda e: self.cancel())
        self.bind("<F1>", lambda e: self.cancel())
        self.hide()
    def show(self, msg="Status: Idle"):
        self.label.config(text=msg)
        self.deiconify()
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.status = "active"
    def hide(self):
        self.withdraw()
        self.status = "idle"
    def running(self, cmd):
        self.cmd = cmd
        self.label.config(text=f"Running: {cmd}\nESC/F1=Cancel")
        self.deiconify()
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.status = "running"
    def done(self, out):
        self.label.config(text=f"Done!\n{out[:100]}...")
        self.after_id = self.after(2200, self.hide)
        self.status = "done"
    def cancel(self, *_):
        if self.proc and self.status == "running":
            self.label.config(text="Cancelling...")
            try: self.proc.terminate()
            except Exception: pass
            self.status = "cancelled"
            self.after_id = self.after(1000, self.hide)

def run_command(cmd, overlay: JemaiOverlay, source="unknown"):
    log(f"[{source}] RUN: {cmd}", "green" if source=="HTTP" else "yellow")
    try:
        overlay.running(cmd)
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        overlay.proc = proc
        output = ""
        for line in iter(proc.stdout.readline, b''):
            if not line: break
            output += line.decode(errors="ignore")
            overlay.label.config(text=f"Running: {cmd}\n{output[-80:]}\nESC/F1=Cancel")
            overlay.update()
            if overlay.status == "cancelled":
                try: proc.terminate()
                except Exception: pass
                break
        proc.wait()
        overlay.done(output if output else "No output")
        overlay.proc = None
    except Exception as e:
        overlay.label.config(text=f"Error: {e}")

def watcher(overlay: JemaiOverlay):
    log("[AGI] Chat/clipboard watcher started.", "cyan")
    last = ""
    while True:
        try:
            text = get_foreground_text()
            if text != last:
                cmd = match_command(text)
                if cmd and overlay.status != "running":
                    log(f"[WINDOW] Detected trigger: {cmd}", "yellow")
                    threading.Thread(target=run_command, args=(cmd, overlay, "WINDOW"), daemon=True).start()
            last = text
        except Exception as e:
            log(f"[WARN] Watcher error: {e}", "yellow")
        time.sleep(POLL_SECONDS)

# ---- HTTP SERVER / EXTENSION ----
class TriggerHandler(BaseHTTPRequestHandler):
    server_version = "JEMAITrigger/1.0"
    extension_last_heartbeat = time.time()
    def do_POST(self):
        if self.path == '/trigger':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode()
            try:
                data = json.loads(body)
                cmd = data.get("cmd")
                if cmd:
                    log(f"[HTTP] Detected trigger: {cmd}", "green")
                    threading.Thread(target=run_command, args=(cmd, overlay, "HTTP"), daemon=True).start()
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"OK")
                    return
            except Exception as e:
                log(f"[HTTP] Trigger error: {e}", "red")
        elif self.path == '/heartbeat':
            TriggerHandler.extension_last_heartbeat = time.time()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            log("[HTTP] Heartbeat received from extension.", "cyan")
            return
        self.send_response(400)
        self.end_headers()
        self.wfile.write(b"FAIL")

def http_server():
    server = HTTPServer(("localhost", 32145), TriggerHandler)
    log("[AGI] HTTP server started on http://localhost:32145/trigger", "cyan")
    server.serve_forever()

# ---- HEARTBEAT/PULSE LOG ----
def agi_heartbeat():
    while True:
        now = time.strftime('%H:%M:%S')
        # Extension heartbeat detection
        ext_ping = TriggerHandler.extension_last_heartbeat
        ago = time.time() - ext_ping
        if ago < 15:
            log(f"[AGI] Heartbeat OK @ {now} (Extension last ping {int(ago)}s ago)", "green")
        else:
            log(f"[AGI] No heartbeat from extension (last: {int(ago)}s ago) @ {now}", "red")
        time.sleep(10)

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    overlay = JemaiOverlay()
    threading.Thread(target=watcher, args=(overlay,), daemon=True).start()
    threading.Thread(target=http_server, daemon=True).start()
    threading.Thread(target=agi_heartbeat, daemon=True).start()
    overlay.mainloop()
