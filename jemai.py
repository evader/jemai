# JEMAI OS FutureFusion v1.0 — Everything, Baked-In, No Bloat
import os, sys, platform, time, datetime, json, sqlite3, shutil, threading, subprocess, socket, base64, random, difflib, glob
from flask import Flask, request, jsonify, render_template_string, send_from_directory, redirect
from flask_socketio import SocketIO, emit
from pathlib import Path

IS_WIN = platform.system() == "Windows"
HOME = str(Path.home())
HUB = os.path.join(HOME, "jemai_hub")
PLUGINS = os.path.join(HUB, "plugins")
VERSIONS = os.path.join(HUB, "versions")
SQLITE = os.path.join(HUB, "jemai_hub.sqlite3")
os.makedirs(HUB, exist_ok=True)
os.makedirs(PLUGINS, exist_ok=True)
os.makedirs(VERSIONS, exist_ok=True)

# ========== RUNTIME INFO, DEVICE ENUM ==========
def get_ip():
    try: s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.connect(("8.8.8.8",80));ip=s.getsockname()[0];s.close();return ip
    except: return "127.0.0.1"
def get_gpu():
    try:
        r = os.popen("nvidia-smi --query-gpu=name,utilization.gpu --format=csv,noheader").read().strip().split("\n")
        return [{"name":l.split(",")[0].strip(),"util":l.split(",")[1].strip()+"%"} for l in r if "," in l]
    except: return []
def get_audio_devices():
    # Dumb stub: in prod, query system
    return ["Default", "Mic1", "Mic2", "Sonos", "TV"]
def get_models():
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags",timeout=4)
        if r.ok: return [m['name'] for m in r.json().get('models',[])]
    except: pass
    return ["llama3:latest","tinyllama:latest"]
def get_status():
    import psutil
    return {
        "host": platform.node(), "ip": get_ip(),
        "type": platform.system().lower(),
        "os": platform.platform(), "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent, "disk": psutil.disk_usage('/').percent,
        "models": get_models(), "gpus": get_gpu(), "plugins": [p[:-3] for p in os.listdir(PLUGINS) if p.endswith('.py')],
        "audio": get_audio_devices(), "cwd": os.getcwd(),
        "time": datetime.datetime.now().isoformat(),
        "versions": sorted(os.listdir(VERSIONS)), "hubfiles": os.listdir(HUB)
    }
# ========== VERSION CONTROL, DIFF, ROLLBACK ==========
def save_version():
    ts = datetime.datetime.now().strftime("%d%m%Y-%H%M%S")
    tgt = os.path.join(VERSIONS, f"{ts}-jemai.py")
    shutil.copy2(__file__, tgt)
def list_versions():
    return sorted([f for f in os.listdir(VERSIONS) if f.endswith(".py")])
def load_version(fn):
    path = os.path.join(VERSIONS, fn)
    return open(path, encoding="utf-8").read() if os.path.exists(path) else ""
def diff_versions(v1, v2):
    t1 = load_version(v1).splitlines()
    t2 = load_version(v2).splitlines()
    return "\n".join(difflib.unified_diff(t1,t2,fromfile=v1,tofile=v2))
def rollback_version(fn):
    path = os.path.join(VERSIONS, fn)
    with open(__file__, "w", encoding="utf-8") as f:
        f.write(open(path,encoding="utf-8").read())
    return True

# ========== PLUGIN ENGINE ==========
PARSERS, PLUGIN_FUNCS = [], {}
def register_parser(fn): PARSERS.append(fn)
def register_plugin(name, func): PLUGIN_FUNCS[name] = func
for fn in os.listdir(PLUGINS):
    if fn.endswith('.py'):
        try:
            code = open(os.path.join(PLUGINS, fn), encoding="utf-8").read()
            ns = {"register_parser": register_parser, "register_plugin": register_plugin}
            exec(code, ns)
        except Exception as e: print(f"[PLUGIN] Fail {fn}: {e}")

# ========== SQLITE3: MEMORY API, CHAT IMPORT ==========
def memory_search(q, limit=10):
    if not os.path.exists(SQLITE): return []
    conn = sqlite3.connect(SQLITE)
    c = conn.cursor()
    c.execute("SELECT hash,source,title,text,date FROM chunks WHERE text LIKE ? LIMIT ?", (f"%{q}%", limit))
    rows = c.fetchall(); conn.close()
    return [{"hash": row[0], "source": row[1], "title": row[2], "text": row[3], "date": row[4]} for row in rows]
def memory_history(n=25):
    if not os.path.exists(SQLITE): return []
    conn = sqlite3.connect(SQLITE); c = conn.cursor()
    c.execute("SELECT hash,source,title,text,date FROM chunks ORDER BY date DESC LIMIT ?", (n,))
    rows = c.fetchall(); conn.close()
    return [{"hash": row[0], "source": row[1], "title": row[2], "text": row[3], "date": row[4]} for row in rows]
def import_chat(file_path):
    for parser in PARSERS:
        try:
            data = parser(file_path)
            if not data: continue
            conn = sqlite3.connect(SQLITE); c = conn.cursor()
            for chunk in data:
                c.execute("INSERT INTO chunks(hash,source,title,text,date,meta) VALUES(?,?,?,?,?,?)",
                    (chunk.get("hash") or str(hash(chunk.get("text"))), chunk.get("source"),
                     chunk.get("title"), chunk.get("text"), chunk.get("date") or "", json.dumps(chunk.get("metadata") or {})))
            conn.commit(); conn.close(); return True
        except Exception as e: print(f"Import fail {file_path}: {e}")
    return False

# ========== FILE EXPLORER, EDITOR ==========
def list_files(path=HUB):
    out = []
    for root, dirs, files in os.walk(path):
        for f in files:
            fp = os.path.relpath(os.path.join(root, f), HUB)
            out.append(fp)
    return out
def read_file(fp):
    p = os.path.join(HUB, fp)
    if not os.path.exists(p): return ""
    return open(p,encoding="utf-8",errors="ignore").read()
def write_file(fp, data):
    p = os.path.join(HUB, fp)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p,"w",encoding="utf-8") as f: f.write(data); return True
def delete_file(fp):
    p = os.path.join(HUB, fp)
    if os.path.exists(p): os.remove(p); return True
    return False
def upload_file(f):
    fn = f.filename
    p = os.path.join(HUB, fn)
    f.save(p); return True

# ========== GROUP CHAT, MULTI-MODEL ==========
def group_chat(msg, models=None):
    out = []
    if not models: models = get_models()
    import requests
    for m in models:
        try:
            r = requests.post("http://localhost:11434/api/generate",json={"model":m,"prompt":msg,"stream":False},timeout=60)
            if r.ok: out.append({"model":m,"resp":r.json().get("response","")})
            else: out.append({"model":m,"resp":f"[Err {r.status_code}]"})
        except Exception as e:
            out.append({"model":m,"resp":f"[ERR] {e}"})
    return out

# ========== OVERLAY, HOTKEY, CLIPBOARD ==========
def spawn_overlay():
    if IS_WIN:
        try: os.system('start python synapz_overlay_v1.1.py')
        except: pass

# ========== HOME ASSISTANT (BAKED) ==========
def ha_call(service, entity_id):
    try:
        import requests
        token = os.environ.get("HOMEASSISTANT_TOKEN")
        url = f"http://homeassistant.local:8123/api/services/{service.replace('.','/')}"
        r = requests.post(url,json={"entity_id":entity_id},headers={"Authorization":"Bearer "+token})
        return r.status_code == 200
    except Exception as e: return False

# ========== WIKI, CHANGELOG, USAGE ==========
def log_event(event, detail=""):
    logf = os.path.join(HUB,"jemai_usage.jsonl")
    with open(logf,"a",encoding="utf-8") as f: f.write(json.dumps({"t":time.time(),"e":event,"d":detail})+"\n")
def read_wiki():
    f = os.path.join(HUB,"JEMAI_WIKI.md")
    return open(f,encoding="utf-8").read() if os.path.exists(f) else ""
def write_wiki(txt):
    f = os.path.join(HUB,"JEMAI_WIKI.md")
    with open(f,"w",encoding="utf-8") as g: g.write(txt)

# ========== THEME ==========
THEMES = {"WarmWinds":"#ffe6d0,#e2e2ea,#775643,#312f2f,#2f323b", "CyberTeal":"#181f2b,#3efcd6,#171f26,#252940,#8fffd9"}
def get_theme(name): return THEMES.get(name,"#181f2b,#e2e2ea,#3efcd6,#252940,#8fffd9").split(",")

# ========== FLASK/WS APP ==========
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route("/")
def main_ui():
    bg,fg,accent,card,chat = get_theme(request.cookies.get("theme","WarmWinds"))
    return render_template_string("""
<!DOCTYPE html><html lang="en"><head>
<title>JEMAI AGI OS</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{margin:0;background:{{bg}};color:{{fg}};font-family:'Segoe UI',Arial,sans-serif;}
.glass{background:rgba(40,43,60,0.88);margin:0 auto 0 auto;max-width:1920px;padding:44px 30px 30px 30px;border-radius:24px;box-shadow:0 7px 38px #2222a9a6;}
.head{font-size:2.2em;font-weight:700;color:{{accent}};}
.slogan{font-size:1.17em;color:#9a8d7d;margin-bottom:24px;}
.mic-btn{background:{{accent}};color:#1a2c22;border:none;border-radius:64px;width:76px;height:76px;font-size:2.2em;cursor:pointer;transition:box-shadow .16s;}
.mic-btn:active{box-shadow:0 0 12px #fffdc0;}
.theme-btn{background:#ffe6d088;border:none;border-radius:8px;padding:6px 18px;margin-left:7px;cursor:pointer;}
@media (max-width:900px){.glass{width:98vw;padding:9vw 2vw;}}
</style>
<script>
function askJemai(){var inp=document.getElementById('inp');var val=inp.value.trim();if(!val)return;
let chat=document.getElementById('chatbox');chat.innerHTML+='<div class="bubble user">'+val+'</div>';
fetch('/api/chat',{method:"POST",headers:{'Content-Type':'application/json'},body:JSON.stringify({q:val})})
.then(r=>r.json()).then(j=>{
chat.innerHTML+='<div class="bubble">'+j.resp+'</div>';chat.scrollTop=chat.scrollHeight;
if(j.voice_url){if(window.jvoice){window.jvoice.pause();}window.jvoice=new Audio(j.voice_url);window.jvoice.play();}
});
inp.value='';}
function themePick(t){document.cookie='theme='+t+';path=/';location.reload();}
function groupChat(){document.getElementById("groupchatbox").innerHTML = "Summoning models..."; fetch('/api/groupchat').then(r=>r.json()).then(j=>{document.getElementById("groupchatbox").innerHTML=JSON.stringify(j.resp)});}
</script>
</head><body>
<div class="glass">
<div class="head">JEMAI <span style="font-size:.65em;font-weight:400;">AGI OS</span></div>
<div class="slogan">Your unified AI: chat, code, voice, RAG, plugins, devices, Home Assistant, everything.</div>
<div style="display:flex;align-items:center;">
<button class="mic-btn" onclick="askJemai()" title="Send"><span>&#127908;</span></button>
<input id="inp" style="flex:1;margin-left:24px;padding:14px;font-size:1.1em;border-radius:12px;border:none;" placeholder="Ask, command, code, search, upload..." onkeydown="if(event.key==='Enter')askJemai()">
<button class="theme-btn" onclick="themePick('WarmWinds')">WarmWinds</button>
<button class="theme-btn" onclick="themePick('CyberTeal')">CyberTeal</button>
<button class="theme-btn" onclick="groupChat()">Group Chat</button>
</div>
<div id="chatbox" style="background:{{chat}};margin-top:32px;border-radius:19px;min-height:240px;max-height:400px;overflow:auto;padding:20px;"></div>
<div id="groupchatbox" style="background:{{card}};margin-top:32px;border-radius:19px;min-height:80px;max-height:160px;overflow:auto;padding:14px;font-size:1.09em;"></div>
<div style="margin:24px 0 0 0;">
<a href="/explorer" style="color:{{accent}};margin-right:22px;">File Explorer</a>
<a href="/vscode" style="color:{{accent}};margin-right:22px;">VSCode</a>
<a href="/plugins" style="color:{{accent}};margin-right:22px;">Plugins</a>
<a href="/wiki" style="color:{{accent}};margin-right:22px;">Wiki/Changelog</a>
<a href="/versions" style="color:{{accent}};margin-right:22px;">Versions</a>
<a href="/settings" style="color:{{accent}};">Settings</a>
</div>
<div style="margin-top:20px;font-size:1em;">
<b>Status:</b> {{stat.host}} | CPU: {{stat.cpu}}% | RAM: {{stat.ram}}% | Disk: {{stat.disk}}% | Models: {{stat.models|join(', ')}}
</div>
</div></body></html>
""",bg=bg,fg=fg,accent=accent,card=card,chat=chat,stat=get_status())

# --- FILE EXPLORER, VSCODE, PLUGIN, SETTINGS, WIKI, VERSION ROUTES ---
@app.route("/explorer")
def explorer_ui():
    files = list_files()
    return render_template_string("""
    <html><body style='background:#232c38;color:#ebebeb;font-family:monospace;padding:36px;'>
    <h2>JEMAI File Explorer</h2>
    <ul>
    {% for f in files %}
      <li><a href='/file/{{f}}' style='color:#58e;'>{{f}}</a>
      <a href='/edit/{{f}}' style='margin-left:14px;color:#fa4;'>[edit]</a>
      <a href='/delete/{{f}}' style='margin-left:14px;color:#f24;'>[delete]</a></li>
    {% endfor %}
    </ul>
    <form action='/upload' method='post' enctype='multipart/form-data'>
      <input type='file' name='f'>
      <button type='submit'>Upload</button>
    </form>
    <a href='/'>Back</a>
    </body></html>
    """, files=files)

@app.route("/file/<path:fp>")
def file_serve(fp):
    return send_from_directory(HUB, fp)

@app.route("/edit/<path:fp>", methods=["GET", "POST"])
def file_edit(fp):
    msg = ""
    if request.method == "POST":
        data = request.form.get("data", "")
        write_file(fp, data)
        msg = "Saved!"
    content = read_file(fp)
    return render_template_string("""
    <html><body style='background:#181f2b;color:#eaeaea;padding:24px;font-family:monospace;'>
    <h2>Edit File: {{fp}}</h2>
    <form method='post'>
    <textarea name='data' style='width:92vw;height:60vh;'>{{content}}</textarea><br>
    <button type='submit'>Save</button>
    <span style='margin-left:17px;color:#8ef;'>{{msg}}</span>
    </form>
    <a href='/explorer'>Back to Explorer</a>
    </body></html>
    """, fp=fp, content=content, msg=msg)

@app.route("/delete/<path:fp>")
def file_delete(fp):
    delete_file(fp)
    return redirect("/explorer")

@app.route("/upload", methods=["POST"])
def file_upload():
    f = request.files.get("f")
    if f: upload_file(f)
    return redirect("/explorer")

@app.route("/vscode")
def vscode_ui():
    # NOTE: You must run VSCode server (code-server) externally for this to work.
    return """
    <html><body style='margin:0;padding:0;background:#131d2b;'>
    <iframe src='http://localhost:8080/' style='border:0;width:99vw;height:99vh;'></iframe>
    <div style='position:fixed;top:14px;right:22px;z-index:12;'><a href='/' style='color:#fffa;'>Back</a></div>
    </body></html>
    """

@app.route("/plugins")
def plugin_ui():
    return render_template_string("""
    <html><body style='background:#223335;color:#e2f1f1;font-family:monospace;padding:28px;'>
    <h2>JEMAI Plugins</h2>
    <ul>
    {% for p in plugins %}
      <li><b>{{p}}</b> <button onclick="runPlugin('{{p}}')">Run</button></li>
    {% endfor %}
    </ul>
    <script>
    function runPlugin(p){
      fetch('/api/plugin/'+p).then(r=>r.json()).then(j=>alert('Plugin: '+p+'\\n'+j.result));
    }
    </script>
    <a href='/'>Back</a>
    </body></html>
    """, plugins=[p[:-3] for p in os.listdir(PLUGINS) if p.endswith('.py')])

@app.route("/wiki", methods=["GET", "POST"])
def wiki_ui():
    msg = ""
    if request.method == "POST":
        txt = request.form.get("wiki", "")
        write_wiki(txt)
        msg = "Saved!"
    wiki = read_wiki()
    return f"""
    <html><body style='background:#232c38;color:#ffdece;font-family:monospace;padding:32px;'>
    <h2>JEMAI WIKI / CHANGELOG</h2>
    <form method='post'>
      <textarea name='wiki' style='width:93vw;height:55vh;'>{wiki}</textarea><br>
      <button type='submit'>Save</button>
      <span style='margin-left:17px;color:#9fc;'>{msg}</span>
    </form>
    <a href='/'>Back</a>
    </body></html>
    """

@app.route("/versions")
def versions_ui():
    vers = list_versions()
    return render_template_string("""
    <html><body style='background:#2f353b;color:#b2fff2;font-family:monospace;padding:32px;'>
    <h2>JEMAI Version History</h2>
    <ul>
    {% for v in vers %}
      <li>
        <b>{{v}}</b>
        <a href='/diff?v1={{v}}&v2=latest' style='color:#ff5;'>[diff latest]</a>
        <a href='/preview/{{v}}' style='color:#2df;'>[preview]</a>
        <a href='/rollback/{{v}}' style='color:#f25;'>[rollback]</a>
      </li>
    {% endfor %}
    </ul>
    <a href='/'>Back</a>
    </body></html>
    """, vers=vers)

@app.route("/diff")
def diff_ui():
    v1 = request.args.get("v1")
    v2 = request.args.get("v2")
    if v2 == "latest": v2 = list_versions()[-1]
    diff = diff_versions(v1, v2)
    return f"""
    <html><body style='background:#191c2c;color:#fa6;font-family:monospace;padding:23px;'>
    <h2>Diff: {v1} vs {v2}</h2>
    <pre style='font-size:1em;background:#181a1e;padding:17px;border-radius:12px;'>{diff}</pre>
    <a href='/versions'>Back to Versions</a>
    </body></html>
    """

@app.route("/preview/<fn>")
def preview_version(fn):
    code = load_version(fn)
    return f"""
    <html><body style='background:#191c2c;color:#cfa;font-family:monospace;padding:23px;'>
    <h2>Preview: {fn}</h2>
    <pre style='font-size:1em;background:#161a1c;padding:13px;border-radius:10px;max-width:98vw;overflow-x:auto;'>{code.replace('<','&lt;')}</pre>
    <a href='/versions'>Back to Versions</a>
    </body></html>
    """

@app.route("/rollback/<fn>")
def rollback_route(fn):
    rollback_version(fn)
    return "<h2>Rollback complete. Restart app to use new version.</h2><a href='/'>Home</a>"

@app.route("/settings", methods=["GET","POST"])
def settings_ui():
    msg = ""
    if request.method == "POST":
        # In future: handle theme, device, integration settings
        msg = "Settings saved (stub)."
    stat = get_status()
    return render_template_string("""
    <html><body style='background:#32343b;color:#ffe8be;padding:36px;font-family:monospace;'>
    <h2>JEMAI Settings & Devices</h2>
    <form method='post'><button type='submit'>Save Settings</button> <span style='color:#afc;'>{{msg}}</span></form>
    <div style='margin-top:18px;'><b>Audio Devices:</b> {{stat.audio}}</div>
    <div><b>Models:</b> {{stat.models}}</div>
    <div><b>Plugins:</b> {{stat.plugins}}</div>
    <div><b>GPUs:</b> {{stat.gpus}}</div>
    <div><b>Working Dir:</b> {{stat.cwd}}</div>
    <a href='/'>Back</a>
    </body></html>
    """, stat=stat, msg=msg)

# --- API ROUTES ---
@app.route("/api/status")
def api_status(): return jsonify(get_status())

@app.route("/api/history")
def api_history(): return jsonify(memory_history(30))

@app.route("/api/files")
def api_files(): return jsonify(list_files())

@app.route("/api/plugins")
def api_plugins(): return jsonify([p[:-3] for p in os.listdir(PLUGINS) if p.endswith('.py')])

@app.route("/api/plugin/<name>")
def api_plugin(name):
    if name in PLUGIN_FUNCS:
        try: return jsonify({"result": PLUGIN_FUNCS[name]()})
        except Exception as e: return jsonify({"result": f"Error: {e}"})
    return jsonify({"result":"Plugin not found"})

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.json or {}
    q = data.get("q","")[:1000]
    resp = "..."
    # RAG, plugin, or model
    if q.lower().startswith("search "):
        resp = "\n\n".join([f"{r['title']}: {r['text'][:80]}" for r in memory_search(q[7:],8)]) or "No memory found."
    elif q.lower().startswith("plugin "):
        p = q[7:].strip()
        if p in PLUGIN_FUNCS: resp = str(PLUGIN_FUNCS[p]())
        else: resp = "Plugin not found."
    elif q.lower() in ["dir","ls"]:
        try: resp = "Files:\n"+"\n".join(os.listdir(HUB))
        except Exception as e: resp = f"[DIR ERROR] {e}"
    else:
        models = get_models()
        if models:
            try:
                import requests
                r = requests.post("http://localhost:11434/api/generate",json={"model":models[0],"prompt":q,"stream":False},timeout=90)
                if r.ok: resp = r.json().get("response","")
                else: resp = f"[Ollama Error {r.status_code}] {r.text}"
            except Exception as e: resp = f"[OLLAMA ERR] {e}"
        else:
            resp = "\n\n".join([f"{r['title']}: {r['text'][:80]}" for r in memory_search(q,3)]) or "No answer found."
    # TTS (very basic, one file only)
    voice_url = None
    try:
        fname = os.path.join(HUB,"jemai_voice.mp3")
        if IS_WIN:
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
    except Exception: pass
    return jsonify({"resp":resp, "voice_url":voice_url})

@app.route("/api/groupchat")
def api_groupchat():
    out = group_chat("Hello JEMAI group!", get_models())
    return jsonify({"resp":out})

@app.route("/hub/<path:filename>")
def serve_hubfile(filename): return send_from_directory(HUB, filename)

# --- MAIN ---
if __name__ == "__main__":
    save_version()
    print("=== JEMAI OS (ALL-IN) v1.0 — https://github.com/evader/jemai")
    socketio.run(app, host="0.0.0.0", port=8181)
