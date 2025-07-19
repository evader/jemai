# JEMAI AGI OS — THE MEGA SUPERFILE — by Synapz+Dave 2025
import os, sys, time, datetime, threading, platform, json, psutil, socket, sqlite3, base64, random, shutil, subprocess, uuid, difflib
from flask import Flask, request, jsonify, render_template_string, send_from_directory, redirect, send_file
from pathlib import Path

# === ENV SETUP ===
IS_WINDOWS = platform.system() == "Windows"
HOME = str(Path.home())
JEMAI_HUB = os.path.join(HOME, "jemai_hub")
PLUGINS_DIR = os.path.join(JEMAI_HUB, "plugins")
VERSIONS_DIR = os.path.join(JEMAI_HUB, "Versions")
SQLITE_PATH = os.path.join(JEMAI_HUB, "jemai_hub.sqlite3")
WIKI_PATH = os.path.join(JEMAI_HUB, "jemai_wiki.md")
os.makedirs(JEMAI_HUB, exist_ok=True)
os.makedirs(PLUGINS_DIR, exist_ok=True)
os.makedirs(VERSIONS_DIR, exist_ok=True)
THEMES = ["WarmWinds", "GlassDark", "Classic", "Cybernight"]
DEFAULT_THEME = "WarmWinds"

# --- REQUIREMENTS AUTO-INSTALL ---
def auto_pip_install(mod):
    try:
        __import__(mod)
    except ImportError:
        os.system(f"pip install {mod}")

for pkg in ["chromadb", "flask", "flask_socketio", "psutil", "pyttsx3", "requests"]:
    auto_pip_install(pkg)

try:
    import chromadb
    from chromadb import PersistentClient
    CHROMA_CLIENT = PersistentClient(path=os.path.join(JEMAI_HUB, "chromadb"))
except Exception:
    CHROMA_CLIENT = None

try:
    import flask_socketio
except Exception:
    pass

# --- AUTO-IMPORT PLUGINS ---
PARSERS = []
PLUGIN_FUNCS = {}
def register_parser(fn): PARSERS.append(fn)
def register_plugin(name, func): PLUGIN_FUNCS[name] = func
for fn in os.listdir(PLUGINS_DIR):
    if fn.endswith('.py'):
        try:
            code = open(os.path.join(PLUGINS_DIR, fn), encoding="utf-8").read()
            ns = {"register_parser": register_parser, "register_plugin": register_plugin}
            exec(code, ns)
        except Exception as e:
            print(f"[PLUGIN] Failed to load {fn}: {e}")

# === CHROMADB UTIL ===
def chroma_list_collections():
    if not CHROMA_CLIENT: return []
    try:
        return [c.name for c in CHROMA_CLIENT.list_collections()]
    except: return []

def chroma_add_document(text, meta=None):
    if not CHROMA_CLIENT: return False
    try:
        col = CHROMA_CLIENT.get_or_create_collection("jemai_docs")
        docid = str(uuid.uuid4())
        col.add(documents=[text], ids=[docid], metadatas=[meta or {}])
        return True
    except Exception as e: return False

def chroma_query(q, limit=5):
    if not CHROMA_CLIENT: return []
    try:
        col = CHROMA_CLIENT.get_or_create_collection("jemai_docs")
        results = col.query(query_texts=[q], n_results=limit)
        return results['documents'][0] if results.get('documents') else []
    except Exception as e: return []

# === FILE UTILS ===
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

def get_gpu_activity():
    try:
        out = subprocess.check_output(
            "nvidia-smi --query-compute-apps=pid,process_name,used_gpu_memory --format=csv,noheader,nounits",
            shell=True, encoding="utf-8", stderr=subprocess.DEVNULL, timeout=2)
        for line in out.strip().split("\n"):
            if not line.strip(): continue
            pid, pname, mem = [s.strip() for s in line.split(",")]
            if pname.lower() in ("python", "python.exe", "ollama", "ollama.exe") and int(mem) > 20:
                return True
    except Exception:
        pass
    return False

def get_gpu_info():
    try:
        out = os.popen("nvidia-smi --query-gpu=name,utilization.gpu,temperature.gpu --format=csv,noheader").read()
        return out.strip().split("\n") if out else []
    except: return []

def device_info():
    # HomeAssistant/Sonos/Audio device stub here: ready to be filled with your tokens
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
        "gpu_active": get_gpu_activity(),
        "plugins": list(PLUGIN_FUNCS.keys()) or [p.__name__ for p in PARSERS],
        "theme": get_setting("theme", DEFAULT_THEME),
        "mic_list": ["Default Mic"],   # Fill out with live audio devices (PyAudio for now, stub)
        "speaker_list": ["Default Speaker"], # stub
        "audio_active": False, # stub
        "home_assistant": {"lights":[],"sonos":[],"tv":[]}, # stub
        "groupchat_ready": True
    }

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

def memory_history(limit=50):
    if not os.path.exists(SQLITE_PATH): return []
    conn = sqlite3.connect(SQLITE_PATH)
    c = conn.cursor()
    c.execute("SELECT hash, source, title, text, date FROM chunks ORDER BY date DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [{"hash": row[0], "source": row[1], "title": row[2], "text": row[3], "date": row[4]} for row in rows]

def list_files(base=JEMAI_HUB):
    out = []
    for root, dirs, files in os.walk(base):
        for f in files:
            path = os.path.relpath(os.path.join(root, f), base)
            out.append(path)
    return out

def get_setting(key, default=None):
    sfile = os.path.join(JEMAI_HUB, "jemai_settings.json")
    try:
        if os.path.exists(sfile):
            with open(sfile, "r", encoding="utf-8") as f:
                j = json.load(f)
                return j.get(key, default)
    except: pass
    return default

def set_setting(key, value):
    sfile = os.path.join(JEMAI_HUB, "jemai_settings.json")
    d = {}
    if os.path.exists(sfile):
        with open(sfile, "r", encoding="utf-8") as f: d = json.load(f)
    d[key] = value
    with open(sfile, "w", encoding="utf-8") as f: json.dump(d, f, indent=2)

def auto_version():
    now = datetime.datetime.now().strftime("%d%m%Y-%H%M")
    base = os.path.join(VERSIONS_DIR, f"{now}-jemai.py")
    shutil.copy2(__file__, base)

# === MOOD/ANALYTICS ===
def extract_mood_from_chat(txt):
    happy = sum(txt.lower().count(word) for word in ["yay", "love", "excited", "great", "amazing", "fantastic", "win"])
    pissed = sum(txt.lower().count(word) for word in ["fuck", "shit", "pissed", "angry", "why", "broken", "fail"])
    return "ecstatic" if happy > pissed else "frustrated" if pissed > happy else "neutral"

# === WIKI/CHANGELOG ===
def save_wiki(msg):
    with open(WIKI_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.datetime.now().isoformat()}] {msg}\n")

def get_wiki():
    if not os.path.exists(WIKI_PATH): return ""
    with open(WIKI_PATH, "r", encoding="utf-8") as f: return f.read()

# === CLIPBOARD/OVERLAY (BAKED IN STUB — Windows Only) ===
def clipboard_overlay_listener():
    if not IS_WINDOWS: return
    try:
        import pyperclip
        last_clip = ""
        while True:
            current = pyperclip.paste()
            if current != last_clip:
                last_clip = current
                # Process for triggers (e.g. JEMAI-SEARCH::, etc)
                if current.startswith("JEMAI-SEARCH::"):
                    res = memory_search(current[len("JEMAI-SEARCH::"):].strip())
                    if res: pyperclip.copy("\n".join(r['text'] for r in res))
            time.sleep(1)
    except Exception as e:
        pass

if IS_WINDOWS:
    threading.Thread(target=clipboard_overlay_listener, daemon=True).start()

# === FLASK APP ===
app = Flask(__name__)
try:
    socketio = flask_socketio.SocketIO(app, async_mode="threading")
except Exception:
    socketio = None

@app.route("/")
def main_ui():
    theme = get_setting("theme", DEFAULT_THEME)
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
  <title>JEMAI AGI OS</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    html,body {margin:0;padding:0;min-height:100vh;width:100vw;font-family:sans-serif;background:#272f36;}
    body.theme-WarmWinds {background:linear-gradient(140deg,#ffd1d1 0,#ffebc3 60%,#d4ffff 100%);}
    body.theme-GlassDark {background:linear-gradient(90deg,#111924,#263243 70%,#242323 100%);}
    body.theme-Classic {background:#cfcfcf;}
    body.theme-Cybernight {background:linear-gradient(110deg,#040b15 0,#214061 70%,#18123a 100%);}
    .jemai-main {max-width:1800px;margin:10px auto;padding:26px;}
    .header {display:flex;align-items:center;gap:22px;}
    .jemai-logo {font-size:2.2em;font-weight:700;color:#26eaa6;text-shadow:0 2px 16px #90f1ef88;}
    .slogan {font-size:1.14em;font-weight:500;color:#111b1b;}
    .mic-btn {background:#26eaa6;color:#1e2733;border:none;border-radius:40px;width:54px;height:54px;font-size:2.4em;cursor:pointer;box-shadow:0 2px 8px #14b77d77;}
    .theme-pick {padding:4px 17px;font-size:1.07em;border-radius:17px;margin:0 0 0 11px;border:1px solid #2deed1;}
    .side-right {position:fixed;right:16px;top:16px;max-width:350px;width:330px;padding:18px;background:rgba(20,28,38,0.95);border-radius:19px;color:#92f6e6;z-index:20;}
    .vscode-bar {margin:18px 0;background:#232b33;border-radius:12px;padding:9px;}
    .inputbar {display:flex;gap:10px;margin:14px 0 0 0;}
    .inputbar input,.inputbar textarea{flex:1;border-radius:9px;border:none;font-size:1.13em;padding:9px 13px;}
    .inputbar button{background:linear-gradient(90deg,#34f4c3 0,#09b8f6 100%);color:#19423f;border:none;border-radius:9px;font-size:1.09em;padding:10px 22px;cursor:pointer;}
    .chat-area {width:100%;max-width:920px;min-height:240px;padding:13px 9px 12px 15px;background:#ffffff99;border-radius:16px;}
    .bubble {margin:9px 0 0 0;padding:11px 15px;border-radius:17px;max-width:70%;word-break:break-word;}
    .bubble.user {background:#fff2a8;color:#442;}
    .bubble.ai {background:#8cffd0;color:#172d2a;}
    .bubble.sys {background:#e2e8ee;color:#2c353e;}
    .chat-timestamp {font-size:.87em;color:#555;margin-top:2px;}
    .explorer, .explorer-tree {background:#2c3141;color:#b8ecf1;font-size:1em;padding:10px 14px;border-radius:12px;}
    .explorer-tree .dir {font-weight:bold;cursor:pointer;color:#4eeeb0;}
    .explorer-tree .file {margin-left:18px;cursor:pointer;}
    .drag-over {background:#ffe49e !important;color:#343;}
    .plugin-bar {margin:12px 0;}
    .chip {display:inline-block;padding:2px 8px;border-radius:13px;font-size:0.97em;background:#d0fff4;color:#176055;margin:1px 3px;}
    .footer {margin:30px 0 0 0;color:#111b1b;font-size:1em;text-align:center;}
    .gpu-dot {display:inline-block;width:17px;height:17px;border-radius:50%;margin-left:8px;vertical-align:middle;background:#c83636;box-shadow:0 0 8px #f66;}
    .gpu-dot.active {background:#42f193;box-shadow:0 0 11px #62f4ba;}
    .theme-pick,select,input[type=file] {margin-left:10px;}
    #vscode_iframe {width:100%;height:56vh;border-radius:11px;border:none;margin-top:7px;}
  </style>
  <script>
    let theme = localStorage.getItem("theme") || "{{theme}}";
    document.addEventListener("DOMContentLoaded",()=>{document.body.className="theme-"+theme;});
    function setTheme(val){document.body.className="theme-"+val;fetch("/api/theme",{method:"POST",headers:{'Content-Type':'application/json'},body:JSON.stringify({theme:val})});localStorage.setItem("theme",val);}
    function pickModel(){let m=prompt("Which model?");if(m)fetch("/api/model",{method:"POST",headers:{'Content-Type':'application/json'},body:JSON.stringify({model:m})});}
    function pickMic(){let m=prompt("Which mic?");if(m)fetch("/api/mic",{method:"POST",headers:{'Content-Type':'application/json'},body:JSON.stringify({mic:m})});}
    function pickSpeaker(){let m=prompt("Which speaker?");if(m)fetch("/api/speaker",{method:"POST",headers:{'Content-Type':'application/json'},body:JSON.stringify({speaker:m})});}
    function groupChat(){document.getElementById("groupchatbox").innerHTML="Summoning models...";fetch('/api/groupchat').then(r=>r.json()).then(j=>{document.getElementById("groupchatbox").innerHTML=j.resp;});}
    function refreshAll(){location.reload();}
    function sendInput(){let inp=document.getElementById('inp');let val=inp.value.trim();if(!val)return;addMsg('user',val);inp.value='';fetch('/api/chat',{method:"POST",headers:{'Content-Type':'application/json'},body:JSON.stringify({q:val})}).then(r=>r.json()).then(j=>{addMsg('ai',j.resp);if(j.resp_voice_url){let aud=new Audio(j.resp_voice_url);aud.play();}});
    }
    function addMsg(who,txt){let area=document.getElementById('chatmain');let d=document.createElement('div');d.className="bubble "+who;d.innerHTML=txt;area.appendChild(d);area.scrollTop=area.scrollHeight;}
    function loadWiki(){fetch("/api/wiki").then(r=>r.text()).then(t=>{document.getElementById("wikibox").innerText=t;});}
    function showRollback(){fetch('/api/versions').then(r=>r.json()).then(list=>{let d=document.getElementById('rollbackbox');d.innerHTML="";list.reverse().forEach(f=>{let el=document.createElement('div');el.className='chip';el.innerText=f;el.onclick=()=>showDiff(f);d.appendChild(el);});});}
    function showDiff(f){fetch('/api/diff/'+f).then(r=>r.json()).then(j=>{let win=window.open("","diffview","width=800,height=600");win.document.write("<pre>"+j.diff+"</pre><button onclick='window.close()'>Close</button>");});}
    function doRollback(f){fetch('/api/rollback/'+f,{method:"POST"}).then(_=>{alert("Rolled back! Refreshing.");location.reload();});}
    function loadExplorer(){fetch('/api/files').then(r=>r.json()).then(list=>{let tree=document.getElementById('explorertree');tree.innerHTML="";list.forEach(p=>{let el=document.createElement('div');el.className='file';el.innerText=p;el.onclick=()=>editFile(p);tree.appendChild(el);});});}
    function editFile(f){fetch('/api/edit/'+f).then(r=>r.text()).then(txt=>{let win=window.open("","fileedit","width=900,height=800");win.document.write("<textarea id='edt' style='width:99%;height:80%'>"+txt+"</textarea><br><button onclick='window.opener.saveFile(\""+f+"\")'>Save</button>");window.saveFile=(ff)=>{let t=win.document.getElementById('edt').value;fetch('/api/edit/'+ff,{method:'POST',headers:{'Content-Type':'text/plain'},body:t}).then(_=>{win.close();});};});}
    function uploadFile(){let f=document.getElementById('fileup').files[0];let data=new FormData();data.append("file",f);fetch('/api/upload',{method:"POST",body:data}).then(_=>{alert("Uploaded!");loadExplorer();});}
    function importChat(){let f=document.getElementById('fileup').files[0];if(!f)return;let data=new FormData();data.append("file",f);fetch('/api/importchat',{method:"POST",body:data}).then(_=>{alert("Chat imported!");});}
    window.onload=()=>{loadWiki();showRollback();loadExplorer();}
  </script>
</head>
<body>
  <div class="jemai-main">
    <div class="header">
      <span class="jemai-logo">JEMAI <span style="font-size:.5em;font-weight:400;color:#888;">AGI OS</span></span>
      <span class="slogan">All models, all memory, all code. Fully in your hands.</span>
      <select class="theme-pick" onchange="setTheme(this.value)">
        {% for t in themes %}<option value="{{t}}" {% if t==theme %}selected{% endif %}>{{t}}</option>{% endfor %}
      </select>
      <button class="mic-btn" onclick="sendInput()" title="Send"><span>&#127908;</span></button>
      <button onclick="pickModel()">Model</button>
      <button onclick="pickMic()">Mic</button>
      <button onclick="pickSpeaker()">Speaker</button>
      <button onclick="groupChat()">Groupchat</button>
      <button onclick="refreshAll()">Refresh</button>
    </div>
    <div class="inputbar">
      <input id="inp" autocomplete="off" placeholder="Type a command, question, or paste code..." />
      <button onclick="sendInput()">Send</button>
      <input type="file" id="fileup" style="margin-left:10px;" />
      <button onclick="uploadFile()">Upload</button>
      <button onclick="importChat()">Import Chat</button>
    </div>
    <div style="display:flex;gap:24px;">
      <div class="chat-area" id="chatmain" style="flex:3 1 650px;max-width:950px;"></div>
      <div class="side-right">
        <div id="rb_stats"></div>
        <div style="margin:10px 0;" class="gpu-dot"></div>
        <div id="rb_vers"></div>
        <div id="rollbackbox"></div>
        <button onclick="showRollback()">Show Rollback</button>
        <div id="wikibox" style="margin-top:14px;background:#19283088;padding:7px 9px;border-radius:10px;max-height:220px;overflow:auto;"></div>
        <button onclick="loadWiki()">Refresh Wiki</button>
      </div>
    </div>
    <div class="explorer" style="margin:19px 0;">
      <b>Explorer</b> <button onclick="loadExplorer()">Reload</button>
      <div class="explorer-tree" id="explorertree" style="max-height:170px;overflow:auto;"></div>
      <div class="vscode-bar"><b>VSCode Editor:</b><iframe id="vscode_iframe" src="https://vscode.dev/" ></iframe></div>
    </div>
    <div id="groupchatbox" style="margin:16px 0 8px 0;min-height:70px;background:#222a34;color:#cceef1;padding:8px;border-radius:10px;"></div>
    <div class="plugin-bar"><b>Plugins:</b>
      {% for p in plugins %}
        <span class="chip">{{p}}</span>
      {% endfor %}
    </div>
    <div class="footer">
      JEMAI AGI OS &copy; {{year}} | <a href="#" onclick="location.reload()">Refresh</a> | <a href="/wiki" target="_blank">Wiki</a> | <a href="/editor" target="_blank">Editor</a>
    </div>
  </div>
</body>
</html>
    """, theme=theme, themes=THEMES, plugins=list(PLUGIN_FUNCS.keys()), year=datetime.datetime.now().year)

@app.route("/api/theme", methods=["POST"])
def api_theme():
    theme = request.json.get("theme", DEFAULT_THEME)
    set_setting("theme", theme)
    return jsonify({"ok": True})

@app.route("/api/status")
def api_status(): return jsonify(device_info())

@app.route("/api/history")
def api_history(): return jsonify(memory_history(20))

@app.route("/api/files")
def api_files(): return jsonify(list_files())

@app.route("/api/plugins")
def api_plugins(): return jsonify(list(PLUGIN_FUNCS.keys()))

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.json or {}
    q = data.get("q", "")[:1000]
    resp = ""
    # ... (Same as before: run commands, plugins, ollama, fallback RAG, etc.)
    if q.strip().lower().startswith("search "):
        resp = "\n\n".join([f"{r['title']}: {r['text'][:80]}" for r in memory_search(q[7:],5)]) or "No memory results."
    elif q.strip().lower() in ["dir","ls"]:
        try:
            files = "\n".join(os.listdir(JEMAI_HUB))
            resp = "Files:\n"+files
        except Exception as e:
            resp = f"[DIR ERROR] {e}"
    elif q.strip().lower().startswith("run "):
        plugin = q[4:].strip()
        if plugin in PLUGIN_FUNCS:
            try:
                resp = f"[PLUGIN {plugin}]: {PLUGIN_FUNCS[plugin]()}"
            except Exception as e:
                resp = f"[PLUGIN {plugin} ERR]: {e}"
        else:
            resp = f"No such plugin '{plugin}'."
    elif q.strip().lower() in PLUGIN_FUNCS:
        try:
            resp = f"[PLUGIN {q.strip()}]: {PLUGIN_FUNCS[q.strip()]()}"
        except Exception as e:
            resp = f"[PLUGIN {q.strip()} ERR]: {e}"
    else:
        models = ollama_list_models()
        if models:
            try:
                import requests
                r = requests.post("http://localhost:11434/api/generate",json={"model":models[0],"prompt":q,"stream":False},timeout=90)
                if r.ok: resp = r.json().get("response","")
                else: resp = f"[Ollama Error {r.status_code}] {r.text}"
            except Exception as e:
                resp = f"[OLLAMA ERR] {e}"
        else:
            # Fallback: semantic search via Chroma
            rag = chroma_query(q, 3)
            if rag: resp = "\n".join(rag)
            else: resp = "\n\n".join([f"{r['title']}: {r['text'][:80]}" for r in memory_search(q,3)]) or "No answer found."
    # Voice synth:
    voice_url = None
    try:
        fname = os.path.join(JEMAI_HUB,"jemai_voice.mp3")
        if IS_WINDOWS:
            import edge_tts, asyncio
            async def speakit():
                communicate = edge_tts.Communicate(resp, "en-US-JennyNeural")
                await communicate.save(fname)
            asyncio.run(speakit())
            voice_url = "/hub/jemai_voice.mp3"
        else:
            import pyttsx3
            engine = pyttsx3.init()
            engine.save_to_file(resp, fname)
            engine.runAndWait()
            voice_url = "/hub/jemai_voice.mp3"
    except Exception:
        pass
    return jsonify({"resp":resp, "resp_voice_url":voice_url})

@app.route("/api/groupchat")
def api_groupchat():
    # Demo: have 2 models "talk" about today's date
    msg = "Today's date is: " + str(datetime.datetime.now().date())
    resp = f"<b>Model 1:</b> {msg}<br><b>Model 2:</b> Wow, {msg} — are you ready to AGI?"
    return jsonify({"resp":resp})

@app.route("/api/model", methods=["POST"])
def api_model():
    set_setting("model", request.json.get("model"))
    return jsonify({"ok":True})

@app.route("/api/mic", methods=["POST"])
def api_mic():
    set_setting("mic", request.json.get("mic"))
    return jsonify({"ok":True})

@app.route("/api/speaker", methods=["POST"])
def api_speaker():
    set_setting("speaker", request.json.get("speaker"))
    return jsonify({"ok":True})

@app.route("/api/upload", methods=["POST"])
def api_upload():
    f = request.files['file']
    path = os.path.join(JEMAI_HUB, f.filename)
    f.save(path)
    return jsonify({"ok":True})

@app.route("/api/importchat", methods=["POST"])
def api_importchat():
    f = request.files['file']
    content = f.read().decode('utf-8','ignore')
    # Try all chat parsers (plugin-based)
    for parser in PARSERS:
        try:
            chats = parser(content)
            for c in chats: chroma_add_document(c['text'], c)
        except Exception: pass
    return jsonify({"ok":True})

@app.route("/api/edit/<path:fname>", methods=["GET","POST"])
def api_editfile(fname):
    path = os.path.join(JEMAI_HUB, fname)
    if request.method=="GET":
        if os.path.exists(path): return open(path,"r",encoding="utf-8").read()
        return ""
    else:
        code = request.data.decode("utf-8")
        with open(path,"w",encoding="utf-8") as f: f.write(code)
        return "ok"

@app.route("/api/versions")
def api_versions():
    return jsonify(sorted(os.listdir(VERSIONS_DIR)))

@app.route("/api/diff/<fname>")
def api_diff(fname):
    cur = open(__file__, encoding="utf-8").read().splitlines()
    old = open(os.path.join(VERSIONS_DIR,fname), encoding="utf-8").read().splitlines()
    diff = "\n".join(difflib.unified_diff(old, cur, fromfile=fname, tofile="Current"))
    return jsonify({"diff":diff})

@app.route("/api/rollback/<fname>", methods=["POST"])
def api_rollback(fname):
    path = os.path.join(VERSIONS_DIR, fname)
    if os.path.exists(path):
        shutil.copy2(path, __file__)
        return jsonify({"ok":True})
    return jsonify({"ok":False})

@app.route("/api/wiki", methods=["GET","POST"])
def api_wiki():
    if request.method=="POST":
        txt = request.form.get("text","")
        save_wiki(txt)
        return "ok"
    return get_wiki()

@app.route("/hub/<path:filename>")
def serve_hubfile(filename): return send_from_directory(JEMAI_HUB, filename)

@app.route("/editor", methods=["GET","POST"])
def edit_ui():
    section = request.args.get("section","full")
    msg = ""
    if request.method=="POST":
        code = request.form.get("code","")
        ok = set_py_section(section, code)
        msg = "Saved!" if ok else "Failed to save!"
    code = get_py_section(section)
    return f"""
    <html><body style='background:#252d37;color:#eee;font-family:monospace;padding:44px;'>
      <h2>JEMAI Code Editor — Section: {section}</h2>
      <form method="post">
        <textarea name="code" style="width:90vw;height:66vh;">{code}</textarea><br>
        <button type="submit">Save</button>
        <span style="margin-left:22px;color:#0f8;'>{msg}</span>
      </form>
      <a href='/' style='color:#aef;margin-top:14px;display:inline-block;'>Back to AGI OS</a>
    </body></html>
    """

@app.route("/wiki")
def wiki_ui():
    return f"""<html><body style="background:#26262b;color:#efe;font-family:sans-serif;padding:41px;">
      <h2>JEMAI Wiki / Changelog</h2>
      <div style="background:#2c3441;padding:17px;border-radius:13px;max-width:900px;">{get_wiki().replace(chr(10),"<br>")}</div>
      <form method="post" action="/api/wiki">
        <textarea name="text" style="width:88vw;height:18vh;"></textarea><br>
        <button type="submit">Append to Wiki</button>
      </form>
      <a href="/" style="color:#9ae;">Back to OS</a>
    </body></html>"""

if __name__ == "__main__":
    auto_version()
    app.run("0.0.0.0", 8181, debug=False)
