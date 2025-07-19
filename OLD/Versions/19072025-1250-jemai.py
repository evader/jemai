import os, sys, time, datetime, threading, platform, json, psutil, socket, sqlite3, base64, random, shutil, subprocess
from flask import Flask, request, jsonify, render_template_string, send_from_directory
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

# === PLUGIN LOADING ===
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

# === UTILS ===
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
    # Returns True if any process (ollama/python) is currently using >2% GPU utilization
    try:
        out = subprocess.check_output(
            "nvidia-smi --query-compute-apps=pid,process_name,used_gpu_memory --format=csv,noheader,nounits",
            shell=True, encoding="utf-8", stderr=subprocess.DEVNULL, timeout=2)
        # We count any python or ollama process using >20MB as 'active'
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
    }

# === MEMORY DB (BAKED-IN SQLITE3) ===
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

# === CONFIG/EDITOR UTILS ===
def get_py_section(section_name):
    # Naive split for major code blocks
    try:
        code = open(__file__, encoding="utf-8").read()
        if section_name == "full": return code
        # For demo: split by "# === <SECTION> ==="
        starts = [i for i,line in enumerate(code.splitlines()) if line.strip().lower().startswith(f"# === {section_name.lower()}")]
        if not starts: return ""
        start = starts[0]
        end = next((i for i in range(start+1, len(code.splitlines())) if code.splitlines()[i].strip().startswith("# ===")), len(code.splitlines()))
        return "\n".join(code.splitlines()[start:end])
    except: return ""

def set_py_section(section_name, new_code):
    # For now: full replace (safe for controlled usage, not for open web)
    if section_name == "full":
        with open(__file__, "w", encoding="utf-8") as f: f.write(new_code)
        return True
    return False

# === FLASK APP ===
app = Flask(__name__)
@app.route("/")
def main_ui():
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
  <title>JEMAI AGI OS</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
  html,body {
    margin:0;padding:0;min-height:100vh;width:100vw;
    font-family: 'Segoe UI', Arial, sans-serif;
    background: radial-gradient(circle at 30% 100%,#2d2c44 0%,#131319 75%) no-repeat;
    color: #fff; overflow-x: hidden;
  }
  .glass {background:rgba(38,43,57,0.7);border-radius:28px;box-shadow:0 7px 48px #3ddad65b;padding:36px 28px 18px 28px;margin:18px 1vw 30px 1vw;width:98vw;max-width:1900px;}
  .jemai-logo {font-size:2.7em;font-weight:700;letter-spacing:0.07em;color:#3ddad6;text-shadow:0 3px 24px #50e7c0c7, 0 2px 1px #155052;margin-bottom:3px;}
  .slogan {font-size:1.17em;font-weight:400;color:#c8e7e4;margin-bottom:27px;letter-spacing:0.03em;}
  .mic-btn {display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(100deg,#65edcf 0,#3ddad6 90%);color:#112e29;border:none;border-radius:54px;width:72px;height:72px;box-shadow:0 4px 26px #3ddad633;font-size:2.1em;transition:box-shadow .16s,background .16s;cursor:pointer;margin:8px 22px 8px 0;outline: none;border: 3px solid #29bdc3;animation: pulse 1.5s infinite;}
  .mic-btn:active,.mic-btn:focus {box-shadow:0 0 12px #9af8e8;}
  @keyframes pulse{0%{box-shadow:0 0 12px #3ddad633;}60%{box-shadow:0 0 44px #3ddad688;}100%{box-shadow:0 0 12px #3ddad633;}}
  .chat-wrap {width:99vw;max-width:1920px;margin:0 auto;display:flex;gap:30px;flex-wrap:wrap;}
  .chat-box {flex:2 1 600px;background:rgba(55,69,95,0.55);border-radius:20px;min-height:380px;max-height:65vh;overflow-y:auto;padding:24px;margin-bottom:10px;box-shadow:0 3px 22px #24576b55;}
  .chat-bubble {margin:0 0 16px 0;padding:13px 19px;border-radius:16px 16px 8px 16px;background:#2fd5c1;color:#122c2b;font-size:1.16em;max-width:70%;display:inline-block;position:relative;word-break:break-word;line-height:1.37em;}
  .chat-bubble.user {background:#fff2a8;color:#463a13;margin-left:auto;border-radius:16px 16px 16px 8px;}
  .chat-timestamp {font-size:0.89em;color:#58dacb;margin-top:2px;margin-bottom:10px;}
  .rightbar {flex:1 1 260px;background:rgba(32,44,48,0.52);border-radius:18px;min-height:120px;padding:20px 12px 10px 18px;color:#6cebd2;font-size:1.06em;box-shadow:0 2px 18px #206f8760;margin-bottom:10px;min-width:260px;max-width:360px;word-break:break-word;}
  .inputbar {display:flex;gap:14px;margin-top:13px;margin-bottom:20px;}
  .inputbar input, .inputbar textarea {flex:1 1 70px;border-radius:9px;border:none;font-size:1.18em;padding:10px 13px;background:#eafffb;color:#19423f;margin-right:7px;outline: none;}
  .inputbar button {background:linear-gradient(100deg,#65edcf 0,#3ddad6 90%);color:#112e29;border:none;border-radius:9px;font-size:1.15em;padding:10px 26px;cursor:pointer;box-shadow:0 3px 16px #3ddad644;transition:box-shadow 0.18s,background 0.14s;}
  .inputbar button:hover {background:#e2fff8;}
  .filebox {margin:8px 0 6px 0;font-size:0.98em;}
  .pill {display:inline-block;padding:2px 11px;border-radius:19px;font-size:1em;background:#5eeec7;color:#1b4e41;margin:2px 7px 2px 0;}
  .chip {display:inline-block;padding:2px 8px;border-radius:13px;font-size:0.95em;background:#fff2a8;color:#837c32;margin:2px 4px;}
  .settings-link {font-size:0.97em;color:#b3eee0;text-decoration:underline;cursor:pointer;float:right;}
  .footer {margin-top:18px;color:#6edac8;font-size:1em;text-align:center;opacity:0.83;border-top:1px solid #235a42;padding-top:10px;}
  .gpu-dot {display:inline-block;width:22px;height:22px;border-radius:50%;margin-left:9px;vertical-align:middle;background:#da3030;box-shadow:0 0 13px #da303088;}
  .gpu-dot.active {background:#38f177;box-shadow:0 0 17px #56fa8c;}
  @media (max-width: 900px) {.glass,.chat-wrap{width:99vw;max-width:100vw;}.rightbar{max-width:99vw;min-width:220px;}}
  </style>
  <script>
  let playingVoice = null;
  function addMsg(who, txt, ts) {
      let box = document.getElementById('chatbox');
      let d = document.createElement('div');
      d.className = "chat-bubble" + (who==="user" ? " user" : "");
      d.innerHTML = txt.replaceAll("\\n","<br>");
      box.appendChild(d);
      let t = document.createElement('div');
      t.className = "chat-timestamp";
      t.innerText = ts;
      box.appendChild(t);
      box.scrollTop = box.scrollHeight;
  }
  function updateStatus(d) {
      document.getElementById("rb_stats").innerHTML = `
        <b>System</b><br>
        Host: <b>${d.hostname}</b> <span class=chip>${d.type}</span>
        <span class="gpu-dot${d.gpu_active?' active':''}" title="GPU in use"></span><br>
        CPU: ${d.cpu}%<br>
        RAM: ${d.ram}%<br>
        Disk: ${d.disk}%<br>
        <b>Ollama:</b> ${(d.ollama_models||[]).map(x=>'<span class="pill">'+x+'</span>').join('')||"None"}<br>
        <b>GPU:</b> ${(d.gpus||[]).map(x=>'<span class="chip">'+x+'</span>').join('')||"None"}<br>
        <b>Plugins:</b> ${(d.plugins||[]).map(x=>'<span class="chip">'+x+'</span>').join('')||"None"}<br>
        <b>Working Dir:</b> ${d.cwd}<br>
        <b>Time:</b> ${d.time.replace('T','<br>')}
      `;
      document.getElementById("rb_vers").innerHTML = `<b>Versions</b><br>${(d.versions||[]).map(x=>'<span class="chip">'+x+'</span>').join('')||"None"}`;
  }
  function refreshRight() {fetch('/api/status').then(r=>r.json()).then(updateStatus);}
  function loadHistory() {fetch('/api/history').then(r=>r.json()).then(hist=>{let div=document.getElementById('rb_mem');if(!div)return;div.innerHTML='<b>Recent Memory</b><br>';hist.forEach(h=>{div.innerHTML+=`<div class='chip' title='${h.text.slice(0,99)}'>${h.title||h.source}</div>`;});});}
  function loadFiles() {fetch('/api/files').then(r=>r.json()).then(list=>{let div=document.getElementById('rb_files');if(!div)return;div.innerHTML='<b>JEMAI Hub Files</b><br>';list.forEach(f=>{div.innerHTML+=`<div class='chip'>${f}</div>`;});});}
  function loadPlugins() {fetch('/api/plugins').then(r=>r.json()).then(list=>{let div=document.getElementById('rb_plugins');if(!div)return;div.innerHTML='<b>Plugins</b><br>';list.forEach(p=>{div.innerHTML+=`<div class='chip' onclick="triggerPlugin('${p}')">${p}</div>`;});});}
  function askJemai() {
    let inp = document.getElementById('inp');
    let val = inp.value.trim();
    if(!val) return;
    addMsg('user', val, new Date().toLocaleTimeString());
    inp.value = '';
    fetch('/api/chat', {method:"POST",headers:{'Content-Type':'application/json'},body:JSON.stringify({q:val})})
    .then(r=>r.json())
    .then(j=>{
      addMsg('jemai',j.resp||"No reply", new Date().toLocaleTimeString());
      if(j.resp_voice_url){
        if(playingVoice) {playingVoice.pause();playingVoice.currentTime=0;}
        playingVoice = new Audio(j.resp_voice_url); playingVoice.play();
      }
    });
  }
  function handleVoice(result) {
    if(result && result.length){
      document.getElementById('inp').value = result;
      askJemai();
    }
  }
  function startMic() {
    if(!('webkitSpeechRecognition' in window)){
      alert("Voice recognition not supported in your browser.");
      return;
    }
    let rec = new webkitSpeechRecognition();
    rec.continuous = false; rec.interimResults = false;
    rec.lang = 'en-US';
    rec.onresult = function(e) {if(e.results.length)handleVoice(e.results[0][0].transcript);}
    rec.start();
  }
  window.onload = ()=>{
    refreshRight(); loadHistory(); loadFiles(); loadPlugins();
    setInterval(refreshRight, 3200);
  }
  function triggerPlugin(name){
    fetch('/api/plugin/'+name).then(r=>r.json()).then(j=>{
      addMsg('jemai', "[PLUGIN "+name+"]<br>"+j.result, new Date().toLocaleTimeString());
    });
  }
  </script>
</head>
<body>
  <div class="glass">
    <div class="jemai-logo">JEMAI <span style="font-size:.56em;color:#fff8;font-weight:500;">AGI OS</span></div>
    <div class="slogan">One command, all intelligence. Your AI, code, and memory workspace.<br>Chat, code, search, control — all in one OS.</div>
    <div style="display:flex;align-items:center;gap:12px;width:100%;">
      <button class="mic-btn" onclick="startMic()" title="Talk to JEMAI"><span>&#127908;</span></button>
      <form style="flex:1;display:inline" onsubmit="askJemai();return false;">
        <div class="inputbar">
          <input id="inp" autocomplete="off" placeholder="Type or paste code, then Enter..." />
          <button type="button" onclick="askJemai()">Send</button>
        </div>
      </form>
    </div>
    <div class="chat-wrap">
      <div class="chat-box" id="chatbox"></div>
      <div class="rightbar">
        <div id="rb_stats"></div>
        <hr style="margin:12px 0;">
        <div id="rb_vers"></div>
        <hr style="margin:12px 0;">
        <div id="rb_mem"></div>
        <hr style="margin:12px 0;">
        <div id="rb_files"></div>
        <hr style="margin:12px 0;">
        <div id="rb_plugins"></div>
      </div>
    </div>
    <div class="footer">
      <span>JEMAI AGI OS &copy; {{year}} | <a href="#" onclick="location.reload()">Refresh</a> | <span class="settings-link" onclick="window.open('/editor')">Editor</span> | <span class="settings-link" onclick="alert('Coming soon: settings and device manager')">About/Settings</span></span>
    </div>
  </div>
</body>
</html>
    """, year=datetime.datetime.now().year)

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

@app.route("/api/status")
def api_status(): return jsonify(device_info())

@app.route("/api/history")
def api_history(): return jsonify(memory_history(20))

@app.route("/api/files")
def api_files(): return jsonify(list_files())

@app.route("/api/plugins")
def api_plugins(): return jsonify(list(PLUGIN_FUNCS.keys()))

@app.route("/api/plugin/<name>")
def api_plugin(name):
    if name in PLUGIN_FUNCS:
        try:
            result = PLUGIN_FUNCS[name]()
            return jsonify({"result": str(result)})
        except Exception as e:
            return jsonify({"result": f"Error: {e}"})
    return jsonify({"result": "Plugin not found"})

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.json or {}
    q = data.get("q", "")[:1000]
    resp = ""
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
            resp = "\n\n".join([f"{r['title']}: {r['text'][:80]}" for r in memory_search(q,3)]) or "No answer found."
    # Voice synth: only one .mp3 at a time, replaced on new request
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
    except Exception as e:
        pass
    return jsonify({"resp":resp, "resp_voice_url":voice_url})

@app.route("/hub/<path:filename>")
def serve_hubfile(filename): return send_from_directory(JEMAI_HUB, filename)

if __name__ == "__main__":
    app.run("0.0.0.0", 8181, debug=False)
