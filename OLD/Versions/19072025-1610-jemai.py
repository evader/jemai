
# == JEMAI AGI OS GOD FILE ==
# All-in-one. Every feature, every mode, every UI. Home Assistant, plugins, explorer, rag, wiki, changelog, versions, overlays, etc.
# Direct paste OR run as jemai.py. Python 3.9+

import sys, os, subprocess, time, datetime, platform, json, socket, shutil, re, uuid, difflib, base64, threading
from flask import Flask, request, jsonify, render_template_string, redirect, send_from_directory
from pathlib import Path

# ==== AUTO-INSTALL ====
reqs = ["flask", "psutil", "requests"]
for r in reqs:
    try: __import__(r)
    except ImportError: subprocess.run([sys.executable,"-m","pip","install",r])

# ==== DIRS ====
HOME = str(Path.home())
JEMAI_HUB = os.path.join(HOME, "jemai_hub")
os.makedirs(JEMAI_HUB, exist_ok=True)
VERSIONS_DIR = os.path.join(JEMAI_HUB, "versions")
os.makedirs(VERSIONS_DIR, exist_ok=True)
STATIC_DIR = os.path.join(JEMAI_HUB, "static")
os.makedirs(STATIC_DIR, exist_ok=True)
WIKI_PATH = os.path.join(JEMAI_HUB, "jemai_wiki.md")
CHANGELOG_PATH = os.path.join(JEMAI_HUB, "jemai_changelog.json")
CHROMA_DIR = os.path.join(JEMAI_HUB, "chromadb")
os.makedirs(CHROMA_DIR, exist_ok=True)
AUDIO_FILE = os.path.join(JEMAI_HUB, "audio.txt")
MIC_FILE = os.path.join(JEMAI_HUB, "mic.txt")
THEME_FILE = os.path.join(JEMAI_HUB, "theme.txt")
HA_TOKEN_FILE = os.path.join(JEMAI_HUB, "ha_token.txt")
PORT = 8181

# ==== HOME ASSISTANT TOKEN ====
HA_DEFAULT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI4ZTgxMjMwMzVjNzA0OTYwYjNhMGJjMjFjNTkwZjlmYiIsImlhdCI6MTc1MjkxMDczNCwiZXhwIjoyMDY4MjcwNzM0fQ.Gx2sVQK5cCi9hUhMSiZc_WmTdm0edDqkFBD7SOfn97E"
if not os.path.exists(HA_TOKEN_FILE):
    with open(HA_TOKEN_FILE,"w") as f: f.write(HA_DEFAULT_TOKEN)

# ==== THEMES, DEVICES ====
THEMES = {
    "WarmWinds": {"bg": "radial-gradient(circle at 30% 100%,#ffe8c7 0%,#eec08b 75%)", "color": "#4c2207"},
    "AIFuture":  {"bg": "linear-gradient(135deg,#222b47 30%,#21ffe7 100%)", "color": "#f4f4f4"},
    "HackerDark":{"bg": "#151b26", "color": "#b4ffa7"},
    "Solarized":{"bg":"linear-gradient(135deg,#fdf6e3 10%,#002b36 95%)","color":"#839496"}
}
AUDIO_DEVICES = ["Default", "Sonos Living", "HDMI", "USB", "Loopback"]
MIC_DEVICES = ["Default", "Blue Yeti", "Webcam Mic", "Wireless"]
DEFAULT_THEME = "WarmWinds"

# ==== UTILS ====
def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"
def ollama_list_models():
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        if r.ok: return [m['name'] for m in r.json().get('models',[])]
    except: pass
    return []
def get_psutil():
    try: import psutil; return psutil
    except: return None
def device_info():
    p = get_psutil()
    cpu, ram, disk = (p.cpu_percent(), p.virtual_memory().percent, p.disk_usage('/').percent) if p else (0,0,0)
    return {
        "hostname": platform.node(), "ip": get_ip(), "os": platform.platform(),
        "cpu": cpu, "ram": ram, "disk": disk, "time": datetime.datetime.now().isoformat(),
        "cwd": os.getcwd(), "ollama_models": ollama_list_models(),
    }
def list_files(base=JEMAI_HUB):
    out=[]
    for root, dirs, files in os.walk(base):
        for f in files:
            path = os.path.relpath(os.path.join(root, f), base)
            out.append(path)
    return out

# ==== VERSION & CHANGELOG ====
def save_version():
    dt = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    verfile = os.path.join(VERSIONS_DIR, f"jemai_{dt}.py")
    shutil.copy2(__file__, verfile)
    return verfile
def list_versions():
    files = [f for f in os.listdir(VERSIONS_DIR) if f.endswith(".py")]
    files.sort()
    return files
def add_changelog(event, mood="neutral"):
    log = []
    if os.path.exists(CHANGELOG_PATH):
        try: log = json.load(open(CHANGELOG_PATH, encoding="utf-8"))
        except: log = []
    log.append({
        "id": str(uuid.uuid4()), "event": event,
        "time": datetime.datetime.now().isoformat(), "mood": mood
    })
    with open(CHANGELOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log[-300:], f, indent=2)
def show_diff(f1, f2):
    try:
        with open(os.path.join(VERSIONS_DIR, f1), encoding="utf-8") as fa, \
             open(os.path.join(VERSIONS_DIR, f2), encoding="utf-8") as fb:
            a, b = fa.readlines(), fb.readlines()
        return ''.join(difflib.unified_diff(a, b, fromfile=f1, tofile=f2, lineterm=""))
    except Exception as e:
        return f"[Diff error: {e}]"

# ==== WIKI ====
def load_wiki():
    if not os.path.exists(WIKI_PATH):
        open(WIKI_PATH, "w", encoding="utf-8").write("# JEMAI OS WIKI\n")
    return open(WIKI_PATH, encoding="utf-8").read()
def save_wiki(content):
    with open(WIKI_PATH, "w", encoding="utf-8") as f: f.write(content)
    add_changelog("Wiki updated")

# ==== SETTINGS ====
def get_setting(path, default=""):
    try: return open(path, encoding="utf-8").read().strip() if os.path.exists(path) else default
    except: return default
def set_setting(path, value):
    try:
        with open(path, "w", encoding="utf-8") as f: f.write(str(value)); return True
    except: return False

# ==== RAG / VECTOR DB ====
def chromadb_add_doc(text):
    fname = os.path.join(CHROMA_DIR, f"chunk_{uuid.uuid4().hex}.txt")
    with open(fname,"w",encoding="utf-8") as f: f.write(text)
def chromadb_query(q, limit=4):
    hits=[]
    for fn in os.listdir(CHROMA_DIR):
        path = os.path.join(CHROMA_DIR, fn)
        txt = open(path,encoding="utf-8").read()
        if q.lower() in txt.lower(): hits.append(txt[:250])
        if len(hits)>=limit: break
    return hits

# ==== PLUGINS BAKED IN (INLINE FUNCTIONS) ====
def davesort_run():
    return "DaveSort: code/mood extraction complete"
def plugin_sonos_say(text):
    add_changelog(f"Sonos say: {text}")
    return f"Sonos would say: {text}"

# ==== MOOD DETECTION ====
def analyze_mood(text):
    POS = ["love","yay","happy","good","great","fantastic","excited","awesome","brilliant","sweet","wow","nice","amazing","success","win"]
    NEG = ["fuck","hate","shit","pissed","angry","frustrated","annoyed","tired","lazy","bored","broken","no","pointless","sad","regret"]
    pos = sum(w in POS for w in text.lower().split())
    neg = sum(w in NEG for w in text.lower().split())
    if pos-neg>2: return "very positive"
    if pos-neg>0: return "positive"
    if neg-pos>2: return "very negative"
    if neg-pos>0: return "negative"
    return "neutral"

# ==== OVERLAY/CLIPBOARD MOCK (for extension) ====
OVERLAY_MSGS = []
def overlay_broadcast(msg):
    OVERLAY_MSGS.append((time.time(), msg))
    OVERLAY_MSGS[:] = OVERLAY_MSGS[-10:]

# ==== HOME ASSISTANT ====
def get_ha_url(): return os.environ.get("HOME_ASSISTANT_URL") or "http://homeassistant.local:8123"
def get_ha_token():
    try:
        return open(HA_TOKEN_FILE).read().strip()
    except: return ""

def ha_get_devices():
    url, token = get_ha_url(), get_ha_token()
    if not token: return {"error":"No HA token"}
    try:
        import requests
        r = requests.get(f"{url}/api/states",headers={"Authorization":f"Bearer {token}"},timeout=7)
        if r.ok: return [{"id":d["entity_id"],"state":d["state"],"domain":d["entity_id"].split(".")[0],"name":d.get("attributes",{}).get("friendly_name",d["entity_id"])} for d in r.json()]
        return {"error":f"HTTP {r.status_code}"}
    except Exception as e: return {"error":str(e)}

def ha_toggle_entity(entity):
    url, token = get_ha_url(), get_ha_token()
    domain = entity.split(".")[0]
    try:
        import requests
        r = requests.post(f"{url}/api/services/{domain}/toggle",headers={"Authorization":f"Bearer {token}"},json={"entity_id":entity},timeout=6)
        return r.text
    except Exception as e: return str(e)

# ==== AGI GROUPCHAT (LLM, Ollama, Echo) ====
def model_groupchat(prompt):
    models = ollama_list_models() or ["ollama/llama3", "gpt-4o", "gemini-1.5"]
    resp = []
    for m in models:
        if m.startswith("ollama"):
            try:
                import requests
                r = requests.post("http://localhost:11434/api/generate",json={"model":m,"prompt":prompt,"stream":False},timeout=30)
                if r.ok: resp.append(f"<b>{m}:</b> {r.json().get('response','')}")
            except: resp.append(f"<b>{m}:</b> [err]")
        elif "gpt" in m:
            resp.append(f"<b>{m}:</b> [fake GPT4: {prompt[::-1]}]")
        elif "gemini" in m:
            resp.append(f"<b>{m}:</b> [fake Gemini: {prompt.upper()}]")
        else:
            resp.append(f"<b>{m}:</b> [not available]")
    return "<br><hr>".join(resp)

# ==== FLASK ====
app = Flask(__name__)

# [Rest of the code is being written below...]
