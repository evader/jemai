# == AUTO-INSTALL REQUIREMENTS ==
import sys, os, subprocess
reqs = ["flask", "psutil", "requests"]
for r in reqs:
    try: __import__(r)
    except ImportError: subprocess.run([sys.executable,"-m","pip","install",r])

import time, datetime, threading, platform, json, socket, shutil, re, uuid, difflib, base64
from flask import Flask, request, jsonify, render_template_string, redirect
from pathlib import Path

# ==== GLOBALS & CONSTANTS ====
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

# ==== HOME ASSISTANT TOKEN: BAKED DEFAULT ====
HA_DEFAULT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI4ZTgxMjMwMzVjNzA0OTYwYjNhMGJjMjFjNTkwZjlmYiIsImlhdCI6MTc1MjkxMDczNCwiZXhwIjoyMDY4MjcwNzM0fQ.Gx2sVQK5cCi9hUhMSiZc_WmTdm0edDqkFBD7SOfn97E"
if not os.path.exists(HA_TOKEN_FILE):
    with open(HA_TOKEN_FILE,"w") as f: f.write(HA_DEFAULT_TOKEN)

# ==== THEMES, DEVICES ====
THEMES = {
    "WarmWinds": {"bg": "radial-gradient(circle at 30% 100%,#ffe8c7 0%,#eec08b 75%)", "color": "#4c2207"},
    "AIFuture":  {"bg": "linear-gradient(135deg,#222b47 30%,#21ffe7 100%)", "color": "#f4f4f4"},
    "HackerDark":{"bg": "#151b26", "color": "#b4ffa7"}
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

@app.route("/")
def main_ui():
    theme = get_setting(THEME_FILE, DEFAULT_THEME)
    dev = device_info()
    code_files = list_files()
    versions = list_versions()
    plugins = ["davesort_run", "plugin_sonos_say"]
    overlays = OVERLAY_MSGS[-5:]
    ollama_models = dev.get("ollama_models", [])
    wiki = load_wiki()
    ha_devices = ha_get_devices()
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>JEMAI AGI OS</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{font-family:'Segoe UI',Arial,sans-serif;background:{{ theme_bg }};color:{{ theme_color }};margin:0;}
.mainnav{background:#fff4;backdrop-filter:blur(10px);padding:14px 28px 8px 33px;font-size:1.21em;display:flex;gap:26px;align-items:center;box-shadow:0 4px 16px #2fd5c144;}
.logo{font-size:2.1em;font-weight:800;color:#2fd5c1;margin-right:18px;}
.section{padding:2vw;}
.chip{display:inline-block;padding:2px 11px;border-radius:15px;font-size:1em;background:#b4fbd6;color:#163f3a;margin:2px 7px 2px 0;}
.code-preview{background:#222c33;color:#e4e6e7;font-family:monospace;padding:13px;border-radius:9px;margin:8px 0;max-width:700px;overflow:auto;white-space:pre;}
.file-opt{cursor:pointer;color:#24bfb6;}
.file-opt:hover{color:#125050;font-weight:700;}
.overlay{position:fixed;bottom:22px;right:22px;background:#333;padding:16px 28px;border-radius:20px;color:#aff;font-size:1.08em;z-index:9999;box-shadow:0 3px 24px #000a;}
.device-tile{background:#fff2;border-radius:11px;padding:13px 19px;margin-bottom:10px;}
.device-name{font-weight:700;font-size:1.1em;}
.device-state{margin-left:10px;}
.toggle-btn{padding:5px 17px;border-radius:7px;background:#26d684;color:#111;border:none;margin-left:19px;cursor:pointer;}
</style>
<script>
function loadFile(f){fetch('/api/file/'+encodeURIComponent(f)).then(r=>r.json()).then(j=>{document.getElementById('fileview').innerHTML='<div class="code-preview">'+(j.code||'[empty]')+'</div>';});}
function runPlugin(p){fetch('/api/plugin/'+p).then(r=>r.json()).then(j=>{alert(j.result);});}
function setTheme(t){fetch('/api/theme/'+t).then(()=>location.reload());}
function sendChat(){let q=document.getElementById('chat_inp').value;fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({q:q})}).then(r=>r.json()).then(j=>{alert(j.resp);});}
function groupChatSend(){let q=document.getElementById("groupchat_inp").value;fetch('/api/groupchat',{method:"POST",headers:{'Content-Type':'application/json'},body:JSON.stringify({q:q})}).then(r=>r.json()).then(j=>{document.getElementById("groupchatbox").innerHTML=j.resp;});}
function ragSearch(){let q=document.getElementById("rag_inp").value;fetch('/api/rag/search?q='+encodeURIComponent(q)).then(r=>r.json()).then(j=>{document.getElementById("ragresults").innerText=JSON.stringify(j,null,2);});}
function haToggle(entity){fetch('/api/ha/toggle/'+encodeURIComponent(entity)).then(()=>location.reload());}
</script>
</head>
<body>
<div class="mainnav">
  <span class="logo">JEMAI</span>
  <b>Theme:</b>
  <select onchange="setTheme(this.value)">
    {% for k in themes %}<option{% if k==theme %} selected{% endif %}>{{ k }}</option>{% endfor %}
  </select>
  <b>Plugins:</b> {% for p in plugins %}<span class="chip" onclick="runPlugin('{{p}}')">{{p}}</span>{% endfor %}
</div>
<div class="section">
  <h2>Chat</h2>
  <input id="chat_inp" style="width:300px;padding:8px;border-radius:8px;">
  <button onclick="sendChat()">Send</button>
  <div style="margin-top:20px;">
    <b>Group Chat:</b> <input id="groupchat_inp" placeholder="Msg for all models" style="padding:8px;border-radius:8px;">
    <button onclick="groupChatSend()">Send</button>
    <div id="groupchatbox" style="margin-top:7px;background:#2222;padding:8px;border-radius:10px;"></div>
  </div>
</div>
<div class="section">
  <h2>File Explorer</h2>
  <div>
    {% for f in code_files %}<span class="file-opt" onclick="loadFile('{{f}}')">{{f}}</span> | {% endfor %}
  </div>
  <div id="fileview"></div>
</div>
<div class="section">
  <h2>Versions</h2>
  <div>{% for v in versions %}{{v}} | {% endfor %}</div>
</div>
<div class="section">
  <h2>Wiki</h2>
  <textarea style="width:90%;height:180px;" id="wiki_edit">{{ wiki }}</textarea>
  <button onclick="fetch('/api/wiki',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:document.getElementById('wiki_edit').value})}).then(()=>alert('Saved'));">Save</button>
</div>
<div class="section">
  <h2>RAG (Semantic Search)</h2>
  <input id="rag_inp" style="width:300px;padding:8px;border-radius:8px;" placeholder="Search text...">
  <button onclick="ragSearch()">Search</button>
  <pre id="ragresults"></pre>
</div>
<div class="section">
  <h2>Home Assistant / Devices</h2>
  {% if ha_devices.error %}
    <div style="color:#b33;font-weight:700;">Error: {{ha_devices.error}}</div>
    <form method="POST" action="/api/ha/token" style="margin-top:19px;">
      <input type="text" name="token" style="width:440px;padding:7px;" placeholder="Paste Home Assistant token here">
      <button type="submit" style="padding:7px 22px;">Save Token</button>
    </form>
  {% else %}
    <div style="max-height:50vh;overflow:auto;">
    {% for d in ha_devices %}
      <div class="device-tile">
        <span class="device-name">{{d.name}}</span>
        <span class="device-state">[{{d.id}}] ({{d.state}})</span>
        {% if d.domain in ["light","switch","fan"] %}
          <button class="toggle-btn" onclick="haToggle('{{d.id}}')">Toggle</button>
        {% endif %}
      </div>
    {% endfor %}
    </div>
  {% endif %}
</div>
<div class="section">
  <h2>Overlay / System</h2>
  <div class="overlay" id="overlay">
    {% for o in overlays %}{{o[1]}}<br>{% endfor %}
  </div>
</div>
</body></html>
""", theme_bg=THEMES[theme]['bg'], theme_color=THEMES[theme]['color'], theme=theme, themes=list(THEMES.keys()),
     code_files=code_files, plugins=plugins, overlays=overlays, versions=versions, wiki=wiki, ha_devices=ha_devices)

# ==== API ROUTES ====
@app.route("/api/file/<path:fname>")
def api_file(fname):
    fpath = os.path.join(JEMAI_HUB, fname)
    if not os.path.exists(fpath): return jsonify({"code":"[File missing]"})
    code = open(fpath, encoding="utf-8", errors="ignore").read()
    return jsonify({"code": code})

@app.route("/api/plugin/<name>")
def api_plugin(name):
    if name == "davesort_run":
        return jsonify({"result": davesort_run()})
    if name == "plugin_sonos_say":
        return jsonify({"result": plugin_sonos_say("Test message")})
    return jsonify({"result":"Not found"})

@app.route("/api/chat", methods=["POST"])
def api_chat():
    q = (request.json or {}).get("q","")
    mood = analyze_mood(q)
    resp = f"Echo: {q[::-1]} (mood: {mood})"
    add_changelog(f"User chat: {q}", mood)
    return jsonify({"resp": resp})

@app.route("/api/groupchat", methods=["POST"])
def api_groupchat():
    q = (request.json or {}).get("q","")
    out = model_groupchat(q)
    add_changelog(f"Groupchat: {q}")
    return jsonify({"resp": out})

@app.route("/api/wiki", methods=["POST"])
def api_wiki():
    content = (request.json or {}).get("content","")
    save_wiki(content)
    return "ok"

@app.route("/api/theme/<theme>")
def api_theme(theme):
    if theme not in THEMES: return "Invalid", 400
    set_setting(THEME_FILE, theme)
    return "ok"

@app.route("/api/rag/search")
def api_rag_search():
    q = request.args.get("q","")
    results = chromadb_query(q, 6)
    return jsonify(results)

@app.route("/api/ha/devices")
def api_ha_devices():
    return jsonify(ha_get_devices())

@app.route("/api/ha/toggle/<entity>")
def api_ha_toggle(entity):
    resp = ha_toggle_entity(entity)
    return jsonify({"resp": resp})

@app.route("/api/ha/token", methods=["POST"])
def api_ha_token():
    token = request.form.get("token","").strip()
    if token:
        with open(HA_TOKEN_FILE,"w") as f: f.write(token)
    return redirect("/")

# ==== VERSIONING/DIFF ====
@app.route("/api/versions")
def api_versions():
    return jsonify(list_versions())

@app.route("/api/version/<vfile>")
def api_version(vfile):
    path = os.path.join(VERSIONS_DIR, vfile)
    if not os.path.exists(path): return jsonify({"code": "[File missing]"})
    code = open(path, encoding="utf-8").read()
    return jsonify({"code": code})

@app.route("/api/diff/<vfile1>/<vfile2>")
def api_diff(vfile1, vfile2):
    diff = show_diff(vfile1, vfile2)
    return jsonify({"diff": diff})

@app.route("/api/changelog")
def api_changelog():
    if not os.path.exists(CHANGELOG_PATH): return jsonify([])
    log = json.load(open(CHANGELOG_PATH,encoding="utf-8"))
    return jsonify(log[-40:])

# ==== MAIN ENTRY ====
if __name__ == "__main__":
    save_version()
    add_changelog("Jemai started")
    app.run(host="0.0.0.0", port=PORT)
