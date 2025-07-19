# == JEMAI AGI OS ULTRA GODMODE ==

import sys, os, subprocess, time, datetime, platform, json, socket, shutil, re, uuid, difflib, base64, threading
from flask import Flask, request, jsonify, render_template_string, redirect

from pathlib import Path

# ==== AUTO-INSTALL ====
reqs = ["flask", "psutil", "requests"]
for r in reqs:
    try: __import__(r)
    except ImportError: subprocess.run([sys.executable,"-m","pip","install",r])

HOME = str(Path.home())
JEMAI_HUB = os.path.join(HOME, "jemai_hub")
os.makedirs(JEMAI_HUB, exist_ok=True)
VERSIONS_DIR = os.path.join(JEMAI_HUB, "versions")
os.makedirs(VERSIONS_DIR, exist_ok=True)
WIKI_PATH = os.path.join(JEMAI_HUB, "jemai_wiki.md")
CHANGELOG_PATH = os.path.join(JEMAI_HUB, "jemai_changelog.json")
CHROMA_DIR = os.path.join(JEMAI_HUB, "chromadb")
os.makedirs(CHROMA_DIR, exist_ok=True)
AUDIO_FILE = os.path.join(JEMAI_HUB, "audio.txt")
MIC_FILE = os.path.join(JEMAI_HUB, "mic.txt")
THEME_FILE = os.path.join(JEMAI_HUB, "theme.txt")
HA_TOKEN_FILE = os.path.join(JEMAI_HUB, "ha_token.txt")
CHATLOG_PATH = os.path.join(JEMAI_HUB, "chatlog.json")
PORT = 8181

# ==== HOME ASSISTANT TOKEN ====
HA_DEFAULT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI4ZTgxMjMwMzVjNzA0OTYwYjNhMGJjMjFjNTkwZjlmYiIsImlhdCI6MTc1MjkxMDczNCwiZXhwIjoyMDY4MjcwNzM0fQ.Gx2sVQK5cCi9hUhMSiZc_WmTdm0edDqkFBD7SOfn97E"
if not os.path.exists(HA_TOKEN_FILE):
    with open(HA_TOKEN_FILE,"w") as f: f.write(HA_DEFAULT_TOKEN)

THEMES = {
    "WarmWinds": {"bg": "radial-gradient(circle at 30% 100%,#ffe8c7 0%,#eec08b 75%)", "color": "#4c2207"},
    "AIFuture":  {"bg": "linear-gradient(135deg,#222b47 30%,#21ffe7 100%)", "color": "#f4f4f4"},
    "HackerDark":{"bg": "#151b26", "color": "#b4ffa7"},
    "Solarized":{"bg":"linear-gradient(135deg,#fdf6e3 10%,#002b36 95%)","color":"#839496"},
    "Ultra": {"bg":"linear-gradient(120deg,#3ff0cb 5%,#fff6 65%,#191d24 100%)","color":"#212b33"}
}
AUDIO_DEVICES = ["Default", "Sonos Living", "HDMI", "USB", "Loopback"]
MIC_DEVICES = ["Default", "Blue Yeti", "Webcam Mic", "Wireless"]
DEFAULT_THEME = "WarmWinds"

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

def save_chat(msg, who="user", model=None, persona=None):
    if not os.path.exists(CHATLOG_PATH): json.dump([], open(CHATLOG_PATH,"w"))
    log = json.load(open(CHATLOG_PATH))
    log.append({"time":datetime.datetime.now().isoformat(),"msg":msg,"who":who,"model":model,"persona":persona})
    json.dump(log[-300:], open(CHATLOG_PATH,"w"))
def load_chat():
    if not os.path.exists(CHATLOG_PATH): return []
    return json.load(open(CHATLOG_PATH))

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
def show_diff(f1, f2, mode="unified"):
    try:
        with open(os.path.join(VERSIONS_DIR, f1), encoding="utf-8") as fa, \
             open(os.path.join(VERSIONS_DIR, f2), encoding="utf-8") as fb:
            a, b = fa.readlines(), fb.readlines()
        if mode=="side":
            return "<table><tr><td><pre>"+''.join(a)+"</pre></td><td><pre>"+''.join(b)+"</pre></td></tr></table>"
        else:
            diff = difflib.unified_diff(a, b, fromfile=f1, tofile=f2, lineterm="")
            return "<pre>"+''.join(diff)+"</pre>"
    except Exception as e:
        return f"[Diff error: {e}]"

def load_wiki():
    if not os.path.exists(WIKI_PATH):
        open(WIKI_PATH, "w", encoding="utf-8").write("# JEMAI OS WIKI\n")
    return open(WIKI_PATH, encoding="utf-8").read()
def save_wiki(content):
    with open(WIKI_PATH, "w", encoding="utf-8") as f: f.write(content)
    add_changelog("Wiki updated")

def wiki_history():
    history = []
    for f in sorted(os.listdir(JEMAI_HUB)):
        if f.startswith("jemai_wiki_v") and f.endswith(".md"):
            history.append(f)
    return history

def save_wiki_version():
    if not os.path.exists(WIKI_PATH): return
    dt = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    tgt = os.path.join(JEMAI_HUB, f"jemai_wiki_v{dt}.md")
    shutil.copy2(WIKI_PATH, tgt)

def get_setting(path, default=""):
    try: return open(path, encoding="utf-8").read().strip() if os.path.exists(path) else default
    except: return default
def set_setting(path, value):
    try:
        with open(path, "w", encoding="utf-8") as f: f.write(str(value)); return True
    except: return False

def chromadb_add_doc(text):
    fname = os.path.join(CHROMA_DIR, f"chunk_{uuid.uuid4().hex}.txt")
    with open(fname,"w",encoding="utf-8") as f: f.write(text)
def chromadb_query(q, limit=4, mode="chroma"):
    hits=[]
    if mode=="simple":
        for fn in os.listdir(CHROMA_DIR):
            path = os.path.join(CHROMA_DIR, fn)
            txt = open(path,encoding="utf-8").read()
            if q.lower() in txt.lower(): hits.append(txt[:250])
            if len(hits)>=limit: break
    else:
        for fn in os.listdir(CHROMA_DIR):
            path = os.path.join(CHROMA_DIR, fn)
            txt = open(path,encoding="utf-8").read()
            if q.lower() in txt.lower(): hits.append(txt[:250])
            if len(hits)>=limit: break
    return hits

def davesort_run():
    return "DaveSort: code/mood extraction complete"
def plugin_sonos_say(text):
    add_changelog(f"Sonos say: {text}")
    return f"Sonos would say: {text}"

def plugin_playground(snippet:str):
    try:
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(snippet, {}, {})
        return buf.getvalue()
    except Exception as e:
        return f"[Plugin Error] {e}"

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

OVERLAY_MSGS = []
def overlay_broadcast(msg):
    OVERLAY_MSGS.append((time.time(), msg))
    OVERLAY_MSGS[:] = OVERLAY_MSGS[-10:]

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

def ha_call_service(domain, service, entity):
    url, token = get_ha_url(), get_ha_token()
    try:
        import requests
        r = requests.post(f"{url}/api/services/{domain}/{service}",
                          headers={"Authorization":f"Bearer {token}"},
                          json={"entity_id":entity})
        return r.text
    except Exception as e:
        return str(e)

def model_groupchat(prompt, models=None, persona=None):
    if not models: models = ollama_list_models() or ["ollama/llama3", "gpt-4o", "gemini-1.5"]
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
    if persona: resp = [f"[{persona.upper()}] {x}" for x in resp]
    return "<br><hr>".join(resp)

app = Flask(__name__)

# ===================== MAIN UI ROUTE =====================
@app.route("/")
def main_ui():
    theme = get_setting(THEME_FILE, DEFAULT_THEME)
    dev = device_info()
    chatlog = load_chat()
    code_files = list_files()
    versions = list_versions()
    plugins = ["davesort_run", "plugin_sonos_say", "playground"]
    overlays = OVERLAY_MSGS[-5:]
    ollama_models = dev.get("ollama_models", [])
    wiki = load_wiki()
    ha_devices = ha_get_devices()
    wiki_versions = wiki_history()
    ui_mode = request.args.get("ui","ultra")
    explorer_mode = request.args.get("explorer","tree")
    rag_mode = request.args.get("rag","chroma")
    wiki_mode = request.args.get("wikimode","editor")
    chat_mode = request.args.get("chatmode","classic")
    file_contents = {}
    if explorer_mode == "inline":
        for f in code_files:
            try:
                file_contents[f] = open(os.path.join(JEMAI_HUB, f), encoding="utf-8").read()
            except Exception:
                file_contents[f] = "[Could not read]"
    else:
        file_contents = {}
    # ... UI HTML omitted for brevity; this would be the same as before ...
    # (just for space; let me know if you want the full HTML/UI pasted here, or just use the version above but swap in this file_contents logic)
    return "ULTRA GODMODE UI RUNNING - see code for UI template"
@app.route("/")
def main_ui():
    theme = get_setting(THEME_FILE, DEFAULT_THEME)
    dev = device_info()
    chatlog = load_chat()
    code_files = list_files()
    versions = list_versions()
    plugins = ["davesort_run", "plugin_sonos_say", "playground"]
    overlays = OVERLAY_MSGS[-5:]
    ollama_models = dev.get("ollama_models", [])
    wiki = load_wiki()
    ha_devices = ha_get_devices()
    wiki_versions = wiki_history()
    ui_mode = request.args.get("ui","ultra")
    explorer_mode = request.args.get("explorer","tree")
    rag_mode = request.args.get("rag","chroma")
    wiki_mode = request.args.get("wikimode","editor")
    chat_mode = request.args.get("chatmode","classic")
    # --- PATCH: Preload all file contents for inline editor ---
    file_contents = {}
    if explorer_mode == "inline":
        for f in code_files:
            try:
                file_contents[f] = open(os.path.join(JEMAI_HUB, f), encoding="utf-8").read()
            except Exception:
                file_contents[f] = "[Could not read]"
    else:
        file_contents = {}

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>JEMAI AGI OS</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{font-family:'Segoe UI',Arial,sans-serif;background:{{theme_bg}};color:{{theme_color}};margin:0;}
.editor{width:95%;height:37vh;margin:9px 0;background:#191d23;color:#eee;border-radius:8px;padding:12px;}
.file-opt{cursor:pointer;color:#24bfb6;}
.file-opt:hover{color:#125050;font-weight:700;}
</style>
<script>
function saveFile(f){let v=document.getElementById('edit_'+f).value;fetch('/api/file/save/'+encodeURIComponent(f),{method:"POST",headers:{'Content-Type':'application/json'},body:JSON.stringify({code:v})}).then(()=>alert('Saved!'));}
</script>
</head>
<body>
<h1>JEMAI Ultra OS (Explorer Inline Edit Mode)</h1>
{% if explorer_mode=="inline" %}
  <div>
  {% for f in code_files %}
    <div>
      <b>{{f}}</b>
      <textarea id="edit_{{f}}" class="editor">{{ file_contents[f] }}</textarea>
      <button onclick="saveFile('{{f}}')">Save</button>
    </div>
  {% endfor %}
  </div>
{% endif %}
</body>
</html>
""",
    theme_bg=THEMES[theme]['bg'], theme_color=THEMES[theme]['color'],
    code_files=code_files, file_contents=file_contents,
    explorer_mode=explorer_mode
)

# ==== FILE LOAD/SAVE, UPLOAD ====
@app.route("/api/file/<path:fname>")
def api_file(fname):
    fpath = os.path.join(JEMAI_HUB, fname)
    if not os.path.exists(fpath): return jsonify({"code":"[File missing]"})
    code = open(fpath, encoding="utf-8", errors="ignore").read()
    return jsonify({"code": code})

@app.route("/api/file/save/<path:fname>", methods=["POST"])
def api_file_save(fname):
    fpath = os.path.join(JEMAI_HUB, fname)
    data = (request.json or {}).get("code","")
    with open(fpath,"w",encoding="utf-8") as f: f.write(data)
    add_changelog(f"Saved file {fname}")
    return "ok"

@app.route("/api/upload", methods=["POST"])
def api_upload():
    f = request.files['file']
    fname = f.filename
    savepath = os.path.join(JEMAI_HUB, fname)
    f.save(savepath)
    add_changelog(f"Uploaded file {fname}")
    return "ok"

# ==== PLUGINS ====
@app.route("/api/plugin/<name>", methods=["GET","POST"])
def api_plugin(name):
    if name == "davesort_run":
        return jsonify({"result": davesort_run()})
    if name == "plugin_sonos_say":
        return jsonify({"result": plugin_sonos_say("Test message")})
    if name == "playground" and request.method=="POST":
        code = (request.json or {}).get("code","")
        return jsonify({"result": plugin_playground(code)})
    return jsonify({"result":"Not found"})

# ==== CHAT / GROUPCHAT / PERSONA ====
@app.route("/api/chat", methods=["POST"])
def api_chat():
    q = (request.json or {}).get("q","")
    model = (request.json or {}).get("model","ollama/llama3")
    persona = (request.json or {}).get("persona","")
    mood = analyze_mood(q)
    resp = f"Echo ({model}): {q[::-1]} (mood: {mood})"
    save_chat(q, who="user", model=model, persona=persona)
    save_chat(resp, who="jemai", model=model, persona=persona)
    add_changelog(f"User chat: {q}", mood)
    return jsonify({"resp": resp})

@app.route("/api/groupchat", methods=["POST"])
def api_groupchat():
    q = (request.json or {}).get("q","")
    out = model_groupchat(q)
    add_changelog(f"Groupchat: {q}")
    return jsonify({"resp": out})

# ==== WIKI, VERSIONS, MARKDOWN ====
@app.route("/api/wiki", methods=["POST"])
def api_wiki():
    content = (request.json or {}).get("content","")
    save_wiki(content)
    save_wiki_version()
    return "ok"

@app.route("/api/wiki/savever")
def api_wiki_savever():
    save_wiki_version()
    return "ok"

@app.route("/api/wiki/ver/<ver>")
def api_wiki_ver(ver):
    fpath = os.path.join(JEMAI_HUB, ver)
    if not os.path.exists(fpath): return jsonify({"content":"[Not found]"})
    code = open(fpath, encoding="utf-8").read()
    return jsonify({"content": code})

# ==== THEME/SETTINGS ====
@app.route("/api/theme/<theme>")
def api_theme(theme):
    if theme not in THEMES: return "Invalid", 400
    set_setting(THEME_FILE, theme)
    return "ok"

# ==== RAG ====
@app.route("/api/rag/search")
def api_rag_search():
    q = request.args.get("q","")
    mode = request.args.get("mode","chroma")
    results = chromadb_query(q, 6, mode)
    return jsonify(results)

# ==== HOME ASSISTANT ====
@app.route("/api/ha/devices")
def api_ha_devices():
    return jsonify(ha_get_devices())

@app.route("/api/ha/toggle/<entity>")
def api_ha_toggle(entity):
    resp = ha_toggle_entity(entity)
    add_changelog(f"Toggled {entity}")
    return jsonify({"resp": resp})

@app.route("/api/ha/token", methods=["POST"])
def api_ha_token():
    token = request.form.get("token","").strip()
    if token:
        with open(HA_TOKEN_FILE,"w") as f: f.write(token)
    add_changelog("HA token updated")
    return redirect("/")

@app.route("/api/ha/service/<domain>/<service>/<entity>")
def api_ha_service(domain,service,entity):
    resp = ha_call_service(domain,service,entity)
    add_changelog(f"Called HA {domain}.{service} on {entity}")
    return jsonify({"resp":resp})

# ==== VERSION/DIFF ====
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
    mode = request.args.get("mode","unified")
    diff = show_diff(vfile1, vfile2, mode)
    return jsonify({"diff": diff})

@app.route("/api/changelog")
def api_changelog():
    if not os.path.exists(CHANGELOG_PATH): return jsonify([])
    log = json.load(open(CHANGELOG_PATH,encoding="utf-8"))
    return jsonify(log[-40:])

if __name__ == "__main__":
    save_version()
    add_changelog("Jemai started")
    app.run(host="0.0.0.0", port=PORT)
