# synapz_overlay.py - Unified Life Search Overlay (Step 969)
import tkinter as tk
from tkinter import simpledialog, messagebox
import threading
import requests
import pyperclip
import keyboard  # pip install keyboard
import sys
import subprocess
import time   # <-- Add this line!

# ---- CONFIG ----
API_USER = "super"
API_PASS = "TechnoAPI69"
API_ENDPOINTS = [
    "http://jemai.local:8089",
    "http://localhost:8089"
]
MAX_RESULTS = 5

# ---- MEMORY API HELPER ----
def memory_search(query, limit=MAX_RESULTS):
    for api in API_ENDPOINTS:
        try:
            resp = requests.get(
                f"{api}/search",
                params={"q": query, "limit": limit},
                auth=(API_USER, API_PASS),
                timeout=8
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if results:
                return results
        except Exception as e:
            print(f"API fail at {api}: {e}", file=sys.stderr)
    return []

# ---- SHELL EXEC (OPTIONAL, Windows only by default) ----
def shell_exec(cmd):
    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, universal_newlines=True, timeout=8)
        return output[:1500]  # Limit size
    except Exception as e:
        return f"Shell error: {e}"

# ---- GUI ----
class SynapzOverlay(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Synapz Unified Search")
        self.geometry("650x80+400+300")
        self.configure(bg="#101026")
        self.attributes("-topmost", True)
        self.resizable(False, False)
        self.overrideredirect(True)  # No window chrome

        # Entry
        self.entry = tk.Entry(self, font=("Consolas", 16), width=55, bg="#1a1a2b", fg="#e0e0ff", insertbackground="#e0e0ff")
        self.entry.pack(padx=15, pady=10)
        self.entry.bind("<Return>", self.run_query)
        self.entry.bind("<Escape>", lambda e: self.close())
        self.entry.bind("<Down>", self.focus_listbox)
        self.entry.focus()

        # Listbox for results
        self.listbox = tk.Listbox(self, font=("Consolas", 12), width=60, height=4, bg="#1a1a2b", fg="#aaaaff")
        self.listbox.pack(padx=15, pady=(0,10))
        self.listbox.bind("<Return>", self.copy_selected)
        self.listbox.bind("<Escape>", lambda e: self.close())
        self.listbox.bind("<Double-Button-1>", self.copy_selected)
        self.results = []

        # Focus trick
        self.after(50, lambda: self.entry.focus_force())

    def focus_listbox(self, event):
        if self.results:
            self.listbox.focus_set()
            self.listbox.selection_set(0)

    def run_query(self, event=None):
        query = self.entry.get().strip()
        self.listbox.delete(0, tk.END)
        self.results = []
        if not query:
            return
        if query.startswith("JEMAI-SEARCH::"):
            search_q = query[len("JEMAI-SEARCH::"):].strip()
            self.results = memory_search(search_q)
            if self.results:
                for r in self.results:
                    text = f"{r['title'] or '[no title]'} | {r['source'] or '[src]'}\n{r['text'][:100].replace('\n',' ')}..."
                    self.listbox.insert(tk.END, text)
            else:
                self.listbox.insert(tk.END, "No results found.")
        elif query.startswith("JEMAI-CMD::"):
            cmd = query[len("JEMAI-CMD::"):].strip()
            out = shell_exec(cmd)
            self.results = [{"text": out, "title": "Shell Output", "source": "local"}]
            self.listbox.insert(tk.END, out if len(out) < 120 else out[:120]+"...")
        elif query.startswith("JEMAI-ACTION::"):
            self.listbox.insert(tk.END, "Agent actions not yet implemented (future: call agent API here)")
        else:
            # Default: memory search
            self.results = memory_search(query)
            if self.results:
                for r in self.results:
                    text = f"{r['title'] or '[no title]'} | {r['source'] or '[src]'}\n{r['text'][:100].replace('\n',' ')}..."
                    self.listbox.insert(tk.END, text)
            else:
                self.listbox.insert(tk.END, "No results found.")

    def copy_selected(self, event=None):
        idx = self.listbox.curselection()
        if not idx:
            idx = (0,)
        if self.results and idx[0] < len(self.results):
            out = self.results[idx[0]]["text"]
            pyperclip.copy(out)
            self.close()
        else:
            self.close()

    def close(self):
        self.destroy()

def launch_overlay():
    overlay = SynapzOverlay()
    overlay.mainloop()

def hotkey_loop():
    print("Hotkey listener active! Press Ctrl+Shift+Space to launch Synapz overlay.")
    keyboard.add_hotkey("ctrl+shift+space", launch_overlay)
    keyboard.wait()  # Blocks forever

if __name__ == "__main__":
    t = threading.Thread(target=hotkey_loop, daemon=True)
    t.start()
    # Keep alive for hotkey, but also allow run as script
    while True:
        time.sleep(3600)
