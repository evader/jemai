import os, sys, time, datetime, threading, platform, json, psutil, socket, sqlite3, base64, random
from flask import Flask, request, jsonify, render_template_string
from pathlib import Path

IS_WINDOWS = platform.system() == "Windows"
HOME = str(Path.home())
JEMAI_HUB = os.path.join(HOME, "jemai_hub")
PLUGINS_DIR = os.path.join(JEMAI_HUB, "plugins")
VERSIONS_DIR = os.path.join(HOME, ".jemai_versions")
SQLITE_PATH = os.path.join(JEMAI_HUB, "jemai_hub.sqlite3")
os.makedirs(JEMAI_HUB, exist_ok=True)
os.makedirs(PLUGINS_DIR, exist_ok=True)
os.makedirs(VERSIONS_DIR, exist_ok=True)

# ========== PLUGIN SYSTEM ==========
PARSERS = []
def register_parser(fn): PARSERS.append(fn)
for fn in os.listdir(PLUGINS_DIR):
    if fn.endswith('.py'):
        try:
            code = open(os.path.join(PLUGINS_DIR, fn), encoding="utf-8").read()
            ns = {}
            exec(code, {"register_parser": register_parser}, ns)
        except Exception as e:
            print(f"[PLUGIN] Failed to load {fn}: {e}")

# ========== SYSTEM/CLUSTER STATUS ==========
def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return "127.0.0.1"

def ollama_list_models():
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        if r.ok:
            return [m['name'] for m in r.json().get('models',[])]
    except: pass
    return []

def get_gpu_info():
    try:
        out = os.popen("nvidia-smi --query-gpu=name,utilization.gpu,temperature.gpu --format=csv,noheader").read()
        return out.strip().split("\n") if out else []
    except: return []

def device_info():
    return {
        "hostname": platform.node(),
        "ip": get_ip(),
        "type": platform.system().lower(),
        "os_version": platform.platform(),
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent,
        "time": datetime.datetime.now().isoformat(),
        "cwd": os.getcwd(),
        "versions": sorted(os.listdir(VERSIONS_DIR)) if os.path.exists(VERSIONS_DIR) else [],
        "ollama_models": ollama_list_models(),
        "gpus": get_gpu_info(),
        "plugins": [p.__name__ for p in PARSERS],
    }

# ========== MEMORY DB (BAKED-IN SQLITE3) ==========
def memory_search(q, limit=5):
    if not os.path.exists(SQLITE_PATH): return []
    conn = sqlite3.connect(SQLITE_PATH)
    c = conn.cursor()
    q_clean = f"%{q.lower()}%"
    c.execute("SELECT hash, source, title, text, date FROM chunks WHERE LOWER(text) LIKE ? LIMIT ?", (q_clean, limit))
    rows = c.fetchall()
    conn.close()
    return [{"hash": row[0], "source": row[1], "title": row[2], "text": row[3], "date": row[4]} for row in rows]

def memory_get(hash_):
    if not os.path.exists(SQLITE_PATH): return None
    conn = sqlite3.connect(SQLITE_PATH)
    c = conn.cursor()
    c.execute("SELECT hash, source, title, text, date, meta FROM chunks WHERE hash = ?", (hash_,))
    row = c.fetchone()
    conn.close()
    if not row: return None
    return {"hash": row[0], "source": row[1], "title": row[2], "text": row[3], "date": row[4], "meta": row[5]}

# ========== CLIPBOARD LISTENER ==========
def clipboard_listener():
    try:
        import pyperclip
        last = ""
        while True:
            txt = pyperclip.paste()
            if txt != last:
                last = txt
                # --- Triggers ---
                if txt.startswith("JEMAI-SEARCH::"):
                    q = txt[len("JEMAI-SEARCH::"):].strip()
                    results = memory_search(q)
                    out = "\n\n".join(
                        f"{r['title']} | {r['source']}\n{r['text'][:120].replace(chr(10),' ')}..." for r in results
                    ) if results else "No results found."
                    pyperclip.copy(out)
                    print("[Clipboard] Search result copied.")
                elif txt.startswith("JEMAI-NAMEGEN::"):
                    names = ["Synthmind", "Signalroot", "Pulsekey", "Haloid", "Vectorus", "Quanta", "Fluxel", "Nodeus"]
                    suggestion = random.choice(names)
                    pyperclip.copy(suggestion)
                    print(f"[Clipboard] Name suggestion copied: {suggestion}")
            time.sleep(1)
    except Exception as e:
        print(f"[CLIPBOARD ERROR] {e}")

# ========== OVERLAY POPUP ==========
def run_overlay():
    try:
        import tkinter as tk, pyperclip
        class Overlay(tk.Tk):
            def __init__(self):
                super().__init__()
                self.title("JEMAI Overlay")
                self.geometry("650x140+450+340")
                self.configure(bg="#101026")
                self.attributes("-topmost", True)
                self.resizable(False, False)
                self.overrideredirect(True)
                self.entry = tk.Entry(self, font=("Consolas", 16), width=55, bg="#1a1a2b", fg="#e0e0ff")
                self.entry.pack(padx=15, pady=10)
                self.entry.bind("<Return>", self.run_query)
                self.entry.bind("<Escape>", lambda e: self.destroy())
                self.entry.focus()
                self.listbox = tk.Listbox(self, font=("Consolas", 12), width=60, height=4, bg="#1a1a2b", fg="#aaaaff")
                self.listbox.pack(padx=15, pady=(0,10))
                self.results = []

            def run_query(self, event=None):
                q = self.entry.get().strip()
                self.listbox.delete(0, tk.END)
                self.results = []
                if not q: return
                if q.startswith("JEMAI-SEARCH::"):
                    search_q = q[len("JEMAI-SEARCH::"):].strip()
                    self.results = memory_search(search_q)
                    if self.results:
                        for r in self.results:
                            text = f"{r['title']} | {r['source']}\n{r['text'][:100].replace('\n',' ')}..."
                            self.listbox.insert(tk.END, text)
                    else:
                        self.listbox.insert(tk.END, "No results found.")
                elif q.startswith("JEMAI-NAMEGEN::"):
                    candidates = ["Synthmind", "Signalroot", "Pulsekey", "Haloid", "Vectorus", "Quanta", "Fluxel", "Nodeus"]
                    suggestion = random.choice(candidates)
                    self.results = [{"text": suggestion}]
                    self.listbox.insert(tk.END, f"Suggested: {suggestion}")
                elif q.startswith("JEMAI-ENCODE::"):
                    val = q[len("JEMAI-ENCODE::"):].strip()
                    enc = base64.b64encode(val.encode()).decode()
                    self.results = [{"text": enc}]
                    self.listbox.insert(tk.END, enc[:120])
                elif q.startswith("JEMAI-DECODE::"):
                    val = q[len("JEMAI-DECODE::"):].strip()
                    try:
                        dec = base64.b64decode(val).decode(errors="ignore")
                        self.results = [{"text": dec}]
                        self.listbox.insert(tk.END, dec[:120])
                    except Exception as e:
                        self.listbox.insert(tk.END, f"Decode error: {e}")
                else:
                    self.listbox.insert(tk.END, "Unknown trigger.")

        app = Overlay()
        app.mainloop()
    except Exception as e:
        print(f"[OVERLAY ERROR] {e}")

# ========== VOICE (NO FAIL) ==========
def say(text):
    try:
        if IS_WINDOWS:
            try:
                import edge_tts, asyncio
                async def speak():
                    communicate = edge_tts.Communicate(str(text), "en-US-JennyNeural")
                    await communicate.save("edge_tts_output.mp3")
                    os.system('start /min wmplayer "edge_tts_output.mp3"')
                asyncio.run(speak())
            except Exception:
                import pyttsx3
                engine = pyttsx3.init()
                engine.say(str(text))
                engine.runAndWait()
        else:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(str(text))
            engine.runAndWait()
    except Exception:
        print(f"[VOICE] {text[:80]}")  # Print fallback

# ========== FLASK REST API & DASHBOARD ==========
app = Flask(__name__)
@app.route("/")
def serve_dashboard():
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <title>JEMAI AGI — Warmwinds Dashboard</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <style>
    html,body {
      min-height:100vh;
      margin:0;padding:0;
      background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
      font-family: 'Segoe UI', Arial, sans-serif;
    }
    .center-wrap {
      max-width: 900px;
      margin: 60px auto 0;
      background: rgba(255,255,255,0.92);
      border-radius: 22px;
      box-shadow: 0 7px 36px #de7e1e25;
      padding: 44px 34px 30px 34px;
    }
    .title {font-size: 2.5em; font-weight: 700; color: #df6f13;}
    .subtitle {font-size: 1.2em; color: #977d5c; margin-bottom: 10px;}
    .stats-table {width: 100%; margin-top:28px;}
    .stats-table th {color: #d24d0c; text-align:left; font-size:1.1em;}
    .stats-table td {padding: 6px 0 6px 7px; font-size: 1.05em; color: #2d2107;}
    .pill {display:inline-block;padding:3px 13px;border-radius:24px;font-size:1em; background: #ffb087; color: #6e3603; margin:2px 7px 2px 0;}
    .chip {display:inline-block; padding:2px 12px; border-radius:16px; font-size:0.95em; background:#ffe4d0; color:#af5400; margin:2px 5px;}
    .buttons {margin-top:30px;}
    button {
      background: linear-gradient(90deg,#ffb68a 0,#ffdab9 100%);
      color: #824300;
      border:none;
      border-radius:14px;
      padding:14px 33px;
      font-size:1.15em;
      margin:0 11px 14px 0;
      box-shadow:0 3px 16px #de7e1e33;
      cursor:pointer;
      transition: box-shadow 0.2s, background 0.2s;
    }
    button:hover {background:#ffecde; box-shadow:0 7px 32px #d24d0c44;}
    .footer {
      margin-top:38px; color:#ba8036; font-size:1em; text-align:center; opacity:0.76;
      border-top:1px solid #eedcc6; padding-top:10px;
    }
    @media(max-width:650px) {
      .center-wrap{padding:18px 2vw;}
      .title{font-size:2em;}
      .stats-table th, .stats-table td{font-size:0.99em;}
      button{font-size:1em;padding:10px 17px;}
    }
    </style>
    <script>
    async function refresh(){
        let s = await fetch("/api/status"); let d = await s.json();
        document.getElementById("stats").innerHTML = `<table class=stats-table>
        <tr><th>Host</th><td>${d.hostname} <span class="chip">${d.type}</span></td></tr>
        <tr><th>IP</th><td>${d.ip}</td></tr>
        <tr><th>CPU</th><td>${d.cpu}%</td></tr>
        <tr><th>RAM</th><td>${d.ram}%</td></tr>
        <tr><th>Disk</th><td>${d.disk}%</td></tr>
        <tr><th>Ollama</th><td>${(d.ollama_models||[]).map(x=>'<span class="pill">'+x+'</span>').join('')||"None"}</td></tr>
        <tr><th>GPU(s)</th><td>${(d.gpus||[]).map(x=>'<span class="chip">'+x+'</span>').join('')||"None"}</td></tr>
        <tr><th>Versions</th><td>${(d.versions||[]).map(x=>'<span class="chip">'+x+'</span>').join('')||"None"}</td></tr>
        <tr><th>Plugins</th><td>${(d.plugins||[]).map(x=>'<span class="chip">'+x+'</span>').join('')||"None"}</td></tr>
        <tr><th>Working Dir</th><td>${d.cwd}</td></tr>
        <tr><th>Time</th><td>${d.time.replace('T','<br>')}</td></tr>
        </table>`;
    }
    window.onload=refresh;
    </script>
</head>
<body>
<div class="center-wrap">
    <div class="title">JEMAI AGI — Warmwinds</div>
    <div class="subtitle">All your AGI system info, Ollama models, and cluster health — one beautiful page.</div>
    <div id="stats"></div>
    <div class="buttons">
      <button onclick="refresh()">Refresh</button>
      <button onclick="fetch('/api/reboot',{method:'POST'});setTimeout(refresh,2500);">Reboot</button>
      <button onclick="fetch('/api/update',{method:'POST'});setTimeout(refresh,2500);">Update</button>
      <button onclick="window.open('/overlay')">Overlay</button>
    </div>
    <div class="footer">
      Warmwinds &copy; 2025 JEMAI AGI OS &mdash; All status real-time. <br>
      Dashboard by Synapz & JEMAI. Powered by Python Flask.<br>
      <span style="font-size:0.9em;color:#e79a4d;">Tip: drop new plugins in <b>/plugins/</b>, they'll appear here!</span>
    </div>
</div>
</body>
</html>
    """)

@app.route("/overlay")
def overlay_popup():
    threading.Thread(target=run_overlay, daemon=True).start()
    return "<b>Overlay launched!</b>"

@app.route("/api/status")
def api_status():
    return jsonify(device_info())

@app.route("/api/search")
def api_search():
    q = request.args.get("q","")
    limit = int(request.args.get("limit",5))
    return jsonify({"results": memory_search(q, limit)})

@app.route("/api/get")
def api_get():
    h = request.args.get("hash")
    res = memory_get(h)
    return jsonify(res) if res else jsonify({"error":"not found"}), 404

@app.route("/api/reboot", methods=["POST"])
def api_reboot():
    threading.Thread(target=lambda: os.system("shutdown /r /t 1" if IS_WINDOWS else "sudo reboot"), daemon=True).start()
    return jsonify({"ok":True})

@app.route("/api/update", methods=["POST"])
def api_update():
    open(os.path.join(JEMAI_HUB,"UPDATED.txt"),"w").write(str(time.time()))
    return jsonify({"ok":True})

# ========== MAIN ==========
if __name__ == "__main__":
    print("[JEMAI] Warmwinds AGI Dashboard is LIVE at http://localhost:8181")
    if IS_WINDOWS:
        threading.Thread(target=clipboard_listener, daemon=True).start()
    app.run(host="0.0.0.0", port=8181)
