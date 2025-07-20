import os, re, sys, time, threading, subprocess
import tkinter as tk
import win32gui, win32con, win32process, win32api
import win32clipboard

TRIGGER_PATTERNS = [
    re.compile(r"jemai::run::(.+)", re.IGNORECASE),
    re.compile(r"jemai::exec::(.+)", re.IGNORECASE),
    re.compile(r"jemai::list::(.+)", re.IGNORECASE)
]
POLL_SECONDS = 1.2

def get_foreground_text():
    """Tries to get the text content of the current active window (fallback: clipboard)."""
    hwnd = win32gui.GetForegroundWindow()
    length = win32gui.SendMessage(hwnd, win32con.WM_GETTEXTLENGTH) + 1
    buf = win32gui.PyMakeBuffer(length)
    win32gui.SendMessage(hwnd, win32con.WM_GETTEXT, length, buf)
    text = str(buf[:-1], errors="ignore")
    if not text.strip():
        # fallback to clipboard if empty
        try:
            win32clipboard.OpenClipboard()
            text = win32clipboard.GetClipboardData()
            win32clipboard.CloseClipboard()
        except Exception:
            pass
    return text

def match_command(text):
    """Scan window text for trigger lines, return command if found."""
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
        self.geometry("420x105+100+40")
        self.resizable(False, False)
        self.label = tk.Label(self, text="Status: Idle", font=("Segoe UI", 15), bg="#222", fg="#fff")
        self.label.pack(fill="both", expand=True, padx=14, pady=12)
        self.protocol("WM_DELETE_WINDOW", self.hide)
        self.status = "idle"
        self.cmd = ""
        self.proc = None
        self.after_id = None
        self.bind("<Escape>", lambda e: self.cancel())
        self.bind("<F1>", lambda e: self.cancel())
        self.hide()
    def show(self, msg="Status: Idle"):
        self.label.config(text=msg)
        self.deiconify()
        self.lift()
        self.status = "active"
    def hide(self):
        self.withdraw()
        self.status = "idle"
    def running(self, cmd):
        self.cmd = cmd
        self.label.config(text=f"Running: {cmd}\nESC/F1=Cancel")
        self.deiconify()
        self.lift()
        self.status = "running"
    def done(self, out):
        self.label.config(text=f"Done!\n{out[:100]}...")
        self.after_id = self.after(2400, self.hide)
        self.status = "done"
    def cancel(self):
        if self.proc and self.status == "running":
            self.label.config(text="Cancelling...")
            try: self.proc.terminate()
            except: pass
            self.status = "cancelled"
            self.after_id = self.after(1000, self.hide)

def run_command(cmd, overlay: JemaiOverlay):
    try:
        overlay.running(cmd)
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        overlay.proc = proc
        output = ""
        for line in iter(proc.stdout.readline, b''):
            output += line.decode(errors="ignore")
            overlay.label.config(text=f"Running: {cmd}\n{output[-80:]}\nESC/F1=Cancel")
            overlay.update()
            if overlay.status == "cancelled":
                break
        proc.wait()
        overlay.done(output if output else "No output")
    except Exception as e:
        overlay.label.config(text=f"Error: {e}")

def watcher():
    print("[JEMAI] Chat watcher started.")
    last = ""
    overlay = JemaiOverlay()
    while True:
        try:
            text = get_foreground_text()
            if text != last:
                cmd = match_command(text)
                if cmd:
                    print(f"[JEMAI] Detected command: {cmd}")
                    t = threading.Thread(target=run_command, args=(cmd, overlay))
                    t.start()
            last = text
        except Exception as e:
            print(f"[JEMAI] Error: {e}")
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    threading.Thread(target=watcher, daemon=True).start()
    tk.mainloop()
