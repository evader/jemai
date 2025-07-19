import os, sys, time, datetime, threading, platform, json, psutil, socket, sqlite3, base64, random, shutil, subprocess, uuid, glob
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_socketio import SocketIO, emit
from pathlib import Path

IS_WINDOWS = platform.system() == "Windows"
HOME = str(Path.home())
JEMAI_HUB = os.path.join(HOME, "jemai_hub")
PLUGINS_DIR = os.path.join(JEMAI_HUB, "plugins")
VERSIONS_DIR = os.path.join(HOME, ".jemai_versions")
SQLITE_PATH = os.path.join(JEMAI_HUB, "jemai_hub.sqlite3")
UPLOADS_DIR = os.path.join(JEMAI_HUB, "uploads")
os.makedirs(JEMAI_HUB, exist_ok=True)
os.makedirs(PLUGINS_DIR, exist_ok=True)
os.makedirs(VERSIONS_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

THEMES = {
    "warmwinds": {"bg": "#f9f5e9", "fg": "#1a2a2f", "accent": "#fab769", "sidebar": "#f2deba"},
    "nightai":   {"bg": "#1a2233", "fg": "#eee", "accent": "#50e7c0", "sidebar": "#232d4d"},
    "matrix":    {"bg": "#011a13", "fg": "#39ff88", "accent": "#1bd43b", "sidebar": "#042d1d"},
}
DEFAULT_THEME = "warmwinds"

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
        if r.ok: return [m['name'] for m in r.json().get('models',[])]
    except: pass
    return []

def get_gpu_activity():
    try:
        out = subprocess.check_output("nvidia-smi --query-compute-apps=pid,process_name,used_gpu_memory --format=csv,noheader,nounits",shell=True,encoding="utf-8",stderr=subprocess.DEVNULL,timeout=2)
        for line in out.strip().split("\n"):
            if not line.strip(): continue
            pid, pname, mem = [s.strip() for s in line.split(",")]
            if pname.lower() in ("python", "python.exe", "ollama", "ollama.exe") and int(mem) > 20: return True
    except: pass
    return False

def get_gpu_info():
    try:
        out = os.popen("nvidia-smi --query-gpu=name,utilization.gpu,temperature.gpu,memory.used --format=csv,noheader").read()
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
        "gpu_active": get_gpu_activity(),
        "plugins": list(PLUGIN_FUNCS.keys()) or [p.__name__ for p in PARSERS],
        "theme": get_theme(),
        "audio_devices": get_audio_devices(),
    }

def get_theme():
    cfg_path = os.path.join(JEMAI_HUB, "ui_theme.json")
    if os.path.exists(cfg_path):
        try:
            j = json.load(open(cfg_path,"r"))
            return j.get("theme", DEFAULT_THEME)
        except: pass
    return DEFAULT_THEME

def set_theme(theme):
    with open(os.path.join(JEMAI_HUB,"ui_theme.json"),"w") as f:
        json.dump({"theme":theme},f)

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

def file_ops(cmd, path, data=None):
    abs_path = os.path.abspath(os.path.join(JEMAI_HUB, path))
    if cmd == "read":
        if not os.path.exists(abs_path): return ""
        return open(abs_path,"r",encoding="utf-8",errors="ignore").read()
    if cmd == "write":
        with open(abs_path,"w",encoding="utf-8") as f: f.write(data)
        return "ok"
    if cmd == "delete":
        os.remove(abs_path)
        return "ok"
    if cmd == "rename" and isinstance(data, str):
        os.rename(abs_path, os.path.join(JEMAI_HUB, data))
        return "ok"
    return "err"

def get_audio_devices():
    if IS_WINDOWS:
        try:
            import sounddevice as sd
            out = sd.query_devices()
            return [x['name'] for x in out]
        except: pass
    return ["System Default"]

def run_ollama_chat(models, prompt, temperature=0.8):
    # Multi-model group chat: chain calls, return dict
    import requests
    outs = {}
    last_out = prompt
    for m in models:
        try:
            r = requests.post("http://localhost:11434/api/generate",json={"model":m,"prompt":last_out,"stream":False,"options":{"temperature":temperature}},timeout=90)
            out = r.json().get("response","") if r.ok else f"[Ollama {m} ERR: {r.status_code}]"
            outs[m] = out
            last_out = out
        except Exception as e:
            outs[m] = f"[Ollama {m} ERR: {e}]"
    return outs

def get_editor_sections():
    code = open(__file__, encoding="utf-8").read()
    section_names = []
    for line in code.splitlines():
        if line.startswith("# === "): section_names.append(line.strip("#= ").split()[0])
    return section_names or ["full"]

def dragdrop_savefile(filename, filedata):
    savepath = os.path.join(JEMAI_HUB, "uploads", filename)
    with open(savepath, "wb") as f: f.write(filedata)
    return savepath

def save_chat_import(name, data):
    base = os.path.join(JEMAI_HUB, "chat_data")
    os.makedirs(base, exist_ok=True)
    fn = name
    if not fn.endswith(".json"): fn += ".json"
    with open(os.path.join(base, fn), "w", encoding="utf-8") as f: f.write(data)
    return fn

# === CLIPBOARD/OVERLAY MIN BAKED-IN ===
def clipboard_listener():
    try:
        import pyperclip
        last = ""
        while True:
            txt = pyperclip.paste()
            if txt != last and txt.strip():
                if txt.startswith("JEMAI-SEARCH::"): pyperclip.copy(" ".join(x['title'] for x in memory_search(txt[14:].strip())))
                if txt.startswith("JEMAI-NAMEGEN::"): pyperclip.copy(random.choice(["Synthmind","Signalroot","Pulsekey","Quanta","Machinality"]))
                last = txt
            time.sleep(0.9)
    except: pass
threading.Thread(target=clipboard_listener, daemon=True).start()

# === FLASK+SOCKETIO ===
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route("/")
def main_ui():
    theme = THEMES.get(get_theme(), THEMES[DEFAULT_THEME])
    models = ollama_list_models()
    editors = get_editor_sections()
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
<title>JEMAI AGI OS Powerhouse</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
html,body{margin:0;padding:0;min-height:100vh;width:100vw;font-family:'Segoe UI',Arial,sans-serif;background:{{theme.bg}};color:{{theme.fg}};overflow-x:hidden;}
.glass{background:rgba(38,43,57,0.7);border-radius:28px;box-shadow:0 7px 48px #3ddad65b;padding:36px 28px 18px 28px;margin:18px 1vw 30px 1vw;width:98vw;max-width:1900px;}
.jemai-logo{font-size:2.7em;font-weight:700;letter-spacing:0.07em;color:{{theme.accent}};text-shadow:0 3px 24px #50e7c0c7,0 2px 1px #155052;margin-bottom:3px;}
.slogan{font-size:1.17em;font-weight:400;color:#c8e7e4;margin-bottom:27px;letter-spacing:0.03em;}
.big-btn{background:linear-gradient(110deg,#fab769 0,#ffce89 90%);color:#17302b;font-size:1.7em;padding:18px 46px;border-radius:38px;margin:20px 6vw;cursor:pointer;box-shadow:0 8px 44px #ffbc7544;font-weight:600;outline:none;border:none;}
.big-btn:active{background:#ffce89;}
.themebar{display:flex;gap:14px;margin:9px 0;}
.theme-btn{padding:7px 18px;border-radius:12px;font-weight:600;border:none;cursor:pointer;background:#eee;color:#1a1a1a;}
.theme-btn.active{background:{{theme.accent}};color:#fff;}
.gpu-bar{height:20px;width:95%;border-radius:7px;background:#292929;margin-bottom:5px;}
.gpu-bar-inner{height:100%;background:#45faad;}
.sidebar{background:{{theme.sidebar}};border-radius:18px;min-width:220px;padding:19px 16px;box-shadow:0 2px 18px #206f8760;}
.explorer{border:2px solid #dde0e9;border-radius:14px;background:#f4f8ff;color:#111;padding:12px;font-size:1.02em;max-height:36vh;overflow:auto;}
.explorer .fileitem{padding:4px 10px;border-radius:8px;margin:2px 0;display:flex;justify-content:space-between;cursor:pointer;}
.explorer .fileitem:hover{background:#d7f5fa;}
.dragover{background:#f4e9ba!important;}
.editor{background:#1a232d;color:#fff;border-radius:14px;padding:19px;margin:11px;}
.vscode-iframe{width:98vw;height:60vh;border:none;border-radius:12px;margin:0;padding:0;}
.groupchat-btn{padding:6px 19px;margin:0 7px 0 0;background:#ffd080;color:#222;border-radius:16px;border:none;font-weight:600;}
@media (max-width:900px){.glass,.sidebar{width:99vw;max-width:100vw;min-width:170px;}.vscode-iframe{width:99vw;}}
</style>
<script src="https://cdn.jsdelivr.net/npm/socket.io-client@4.7.5/dist/socket.io.min.js"></script>
<script>
let socket = io();
let curTheme = "{{theme_name}}";
function setTheme(thm){fetch('/api/theme',{method:"POST",headers:{'Content-Type':'application/json'},body:JSON.stringify({theme:thm})}).then(_=>location.reload());}
function askJemai(){let inp=document.getElementById('inp');let val=inp.value.trim();if(!val)return;addMsg('user',val,new Date().toLocaleTimeString());inp.value='';socket.emit('chat',{q:val,models:getModels()});}
function addMsg(who,txt,ts){let box=document.getElementById('chatbox');let d=document.createElement('div');d.className="chat-bubble"+(who==="user"?" user":"");d.innerHTML=txt.replaceAll("\\n","<br>");box.appendChild(d);let t=document.createElement('div');t.className="chat-timestamp";t.innerText=ts;box.appendChild(t);box.scrollTop=box.scrollHeight;}
function getModels(){let sel=[];document.querySelectorAll('.model-sel:checked').forEach(c=>sel.push(c.value));return sel;}
function setAudioDevice(dev){fetch('/api/audio',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device:dev})});}
function handleFileDrop(ev){ev.preventDefault();let dt=ev.dataTransfer;for(let i=0;i<dt.files.length;i++){let file=dt.files[i];let fr=new FileReader();fr.onload=function(e){socket.emit('filedrop',{name:file.name,data:e.target.result.split(",")[1]});};fr.readAsDataURL(file);}}
function dragOver(ev){ev.preventDefault();ev.currentTarget.classList.add('dragover');}
function dragLeave(ev){ev.preventDefault();ev.currentTarget.classList.remove('dragover');}
socket.on('msg',d=>{addMsg(d.who,d.txt,d.ts);});
socket.on('refreshExplorer',()=>{loadExplorer();});
function loadExplorer(){
fetch('/api/files').then(r=>r.json()).then(list=>{
let div=document.getElementById('explorer');div.innerHTML='';
list.forEach(f=>{
let d=document.createElement('div');
d.className='fileitem';d.innerHTML=f+' <button onclick="editFile(\\''+f+'\\')">Edit</button>';
d.onclick=function(ev){if(ev.target.tagName!="BUTTON")editFile(f);};
div.appendChild(d);
});});
}
function editFile(f){
fetch('/api/file?path='+encodeURIComponent(f)).then(r=>r.json()).then(j=>{
document.getElementById('edit-filename').value=f;
document.getElementById('edit-content').value=j.data||'';
document.getElementById('editor-section').style.display='block';
});
}
function saveEditFile(){
let f=document.getElementById('edit-filename').value;
let d=document.getElementById('edit-content').value;
fetch('/api/file',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:f,data:d})}).then(_=>{document.getElementById('editor-section').style.display='none';loadExplorer();});
}
window.onload=()=>{loadExplorer();}
</script>
</head>
<body>
<div class="glass">
<div class="jemai-logo">JEMAI <span style="font-size:.56em;color:#fff8;font-weight:500;">AGI OS</span></div>
<div class="slogan">AGI, code, and memory workspace — voice, VSCode, group chat, drag-drop, GPU, RAG, plugins, cloud.</div>
<div class="themebar">
{% for t in themes %}
  <button class="theme-btn{% if theme_name==t %} active{% endif %}" onclick="setTheme('{{t}}')">{{t}}</button>
{% endfor %}
</div>
<div style="display:flex;gap:38px;align-items:flex-start;">
  <div style="flex:2;">
    <form onsubmit="askJemai();return false;" style="margin-bottom:10px;">
      <input id="inp" autocomplete="off" placeholder="Type or paste code..." style="font-size:1.16em;padding:11px;width:60vw;border-radius:13px;margin-right:12px;">
      <button class="big-btn" type="submit">&#127908; Talk to JEMAI</button>
    </form>
    <div>
      <span>Models:</span>
      {% for m in models %}
        <label><input type="checkbox" class="model-sel" value="{{m}}" checked> {{m}}</label>
      {% endfor %}
      <button class="groupchat-btn" onclick="askJemai()">Group Chat</button>
    </div>
    <div class="chat-box" id="chatbox" style="min-height:240px;max-height:45vh;overflow-y:auto;margin-top:14px;"></div>
    <iframe src="https://vscode.dev" class="vscode-iframe"></iframe>
    <div style="margin-top:10px;">
      <div><b>GPU(s):</b> {% for g in gpu %}<div class="gpu-bar"><div class="gpu-bar-inner" style="width:{{g.util}}%"></div> {{g.name}} ({{g.util}}% - {{g.temp}}°C - {{g.mem}}MB)</div>{% endfor %}</div>
      <div><b>Audio Devices:</b> <select onchange="setAudioDevice(this.value)">{% for a in audio %}<option>{{a}}</option>{% endfor %}</select></div>
    </div>
  </div>
  <div class="sidebar" style="flex:1;" ondrop="handleFileDrop(event)" ondragover="dragOver(event)" ondragleave="dragLeave(event)">
    <b>File Explorer (drag & drop import)</b>
    <div id="explorer" class="explorer"></div>
    <div id="editor-section" style="display:none;">
      <input id="edit-filename" style="width:70%;" readonly><br>
      <textarea id="edit-content" style="width:98%;height:14vh;"></textarea><br>
      <button onclick="saveEditFile()">Save</button>
      <button onclick="document.getElementById('editor-section').style.display='none'">Cancel</button>
    </div>
    <hr>
    <div><b>Plugins:</b> {% for p in plugins %} <span class="chip">{{p}}</span> {% endfor %}</div>
    <hr>
    <div><b>Theme:</b> {{theme_name}}</div>
  </div>
</div>
<div class="footer">JEMAI AGI OS &copy; {{year}} | Powerhouse Mode | <a href="/editor">Full Editor</a></div>
</div>
<script>window.onload=()=>{loadExplorer();}</script>
</body>
</html>
""", year=datetime.datetime.now().year, models=ollama_list_models(), plugins=list(PLUGIN_FUNCS.keys()), gpu=[{"name":g.split(",")[0],"util":g.split(",")[1],"temp":g.split(",")[2],"mem":g.split(",")[3]} for g in get_gpu_info() if "," in g], audio=get_audio_devices(), theme=THEMES.get(get_theme()), theme_name=get_theme(), themes=THEMES.keys())

@app.route("/api/theme", methods=["POST"])
def api_theme():
    set_theme(request.json.get("theme", DEFAULT_THEME))
    return jsonify({"ok":True})

@app.route("/api/files")
def api_files(): return jsonify(list_files())

@app.route("/api/file", methods=["GET","POST"])
def api_file():
    if request.method=="GET":
        path=request.args.get("path","")
        return jsonify({"data":file_ops("read",path)})
    else:
        d=request.json
        file_ops("write",d["path"],d["data"])
        return jsonify({"ok":True})

@app.route("/api/plugins")
def api_plugins(): return jsonify(list(PLUGIN_FUNCS.keys()))

@app.route("/api/audio", methods=["POST"])
def api_audio():
    # Here: set default audio device (for future expansion)
    return jsonify({"ok":True})

@app.route("/api/import_chat", methods=["POST"])
def api_import_chat():
    data = request.files['file']
    fn = save_chat_import(data.filename, data.read().decode("utf-8"))
    return jsonify({"ok":True, "filename":fn})

@socketio.on('chat')
def chat_ws(msg):
    q = msg.get('q','')
    models = msg.get('models', ollama_list_models())
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    if isinstance(models, str): models = [models]
    outs = run_ollama_chat(models, q)
    for m, resp in outs.items():
        emit('msg', {'who':m, 'txt':resp, 'ts':ts})

@socketio.on('filedrop')
def filedrop_ws(msg):
    name = msg['name']
    data = base64.b64decode(msg['data'])
    dragdrop_savefile(name, data)
    emit('refreshExplorer', {})

@app.route("/hub/<path:filename>")
def serve_hubfile(filename): return send_from_directory(JEMAI_HUB, filename)

@app.route("/editor", methods=["GET","POST"])
def edit_ui():
    section = request.args.get("section","full")
    msg = ""
    if request.method=="POST":
        code = request.form.get("code","")
        with open(__file__, "w", encoding="utf-8") as f: f.write(code)
        msg = "Saved!" if code else "Failed to save!"
    code = open(__file__, encoding="utf-8").read()
    return f"""<html><body style='background:#252d37;color:#eee;font-family:monospace;padding:44px;'>
      <h2>JEMAI Code Editor — Section: {section}</h2>
      <form method="post"><textarea name="code" style="width:90vw;height:66vh;">{code}</textarea><br>
      <button type="submit">Save</button><span style="margin-left:22px;color:#0f8;'>{msg}</span>
      </form>
      <a href='/' style='color:#aef;margin-top:14px;display:inline-block;'>Back to AGI OS</a></body></html>"""

if __name__=="__main__":
    socketio.run(app, host="0.0.0.0", port=8181)
