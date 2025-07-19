import os, sys, time, datetime, threading, platform, json, psutil, socket, sqlite3, base64, random, shutil, subprocess, re
from flask import Flask, request, jsonify, render_template_string, send_from_directory, redirect
from pathlib import Path

# === GLOBALS ===
IS_WINDOWS = platform.system() == "Windows"
HOME = str(Path.home())
JEMAI_HUB = os.path.join(HOME, "jemai_hub")
PLUGINS_DIR = os.path.join(JEMAI_HUB, "plugins")
VERSIONS_DIR = os.path.join(JEMAI_HUB, "OLD", "Versions")
WIKI_PATH = os.path.join(JEMAI_HUB, "jemai_wiki.md")
DAVESORT_DIR = os.path.join(JEMAI_HUB, "davesort")
SQLITE_PATH = os.path.join(JEMAI_HUB, "jemai_hub.sqlite3")
os.makedirs(JEMAI_HUB, exist_ok=True)
os.makedirs(PLUGINS_DIR, exist_ok=True)
os.makedirs(VERSIONS_DIR, exist_ok=True)
os.makedirs(DAVESORT_DIR, exist_ok=True)

# === PLUGIN SYSTEM ===
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

def list_files(base=JEMAI_HUB):
    out = []
    for root, dirs, files in os.walk(base):
        for f in files:
            path = os.path.relpath(os.path.join(root, f), base)
            out.append(path)
    return out

# === MEMORY DB ===
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

# === WIKI & CHANGELOG SYSTEM ===
def save_wiki(content):
    with open(WIKI_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    return True

def load_wiki():
    if not os.path.exists(WIKI_PATH):
        save_wiki("# JEMAI OS WIKI\n\n- Add your notes, usage tips, and docs here!\n")
    with open(WIKI_PATH, "r", encoding="utf-8") as f:
        return f.read()

def list_versions():
    versions = []
    for f in os.listdir(VERSIONS_DIR):
        if f.endswith(".py"):
            full = os.path.join(VERSIONS_DIR, f)
            try:
                ts = os.path.getmtime(full)
                versions.append((f, ts))
            except Exception: continue
    versions.sort(key=lambda x: -x[1])
    return versions

def show_version_diff(fn1, fn2):
    try:
        from difflib import unified_diff
        with open(os.path.join(VERSIONS_DIR, fn1), encoding="utf-8") as f1, \
             open(os.path.join(VERSIONS_DIR, fn2), encoding="utf-8") as f2:
            lines1 = f1.readlines()
            lines2 = f2.readlines()
        diff = unified_diff(lines1, lines2, fromfile=fn1, tofile=fn2, lineterm="")
        return ''.join(diff)
    except Exception as e:
        return f"[DIFF ERROR] {e}"

# === DAVE SORT (CODE & MOOD EXTRACTOR) ===
def davesort_run():
    OUT_DIR = Path(DAVESORT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_FILE = OUT_DIR / "davesort_index.json"
    MASTER_FILE = OUT_DIR / "davesort_masterlog.json"
    index_log, master_log = [], []
    POSITIVE_WORDS = set("love yay happy good great fantastic excited awesome brilliant sweet wow nice amazing success win".split())
    NEGATIVE_WORDS = set("fuck hate shit pissed off angry frustrated annoyed tired lazy bored broken no pointless sad regret".split())
    def guess_sentiment(text):
        pos = sum(w in POSITIVE_WORDS for w in text.lower().split())
        neg = sum(w in NEGATIVE_WORDS for w in text.lower().split())
        if pos-neg > 2: return "very positive"
        if pos-neg > 0: return "positive"
        if neg-pos > 2: return "very negative"
        if neg-pos > 0: return "negative"
        return "neutral"
    def extract_code_blocks(text):
        CODE_BLOCK_REGEX = re.compile(r"```(\w+)?\s*([\s\S]*?)```", re.MULTILINE)
        blocks = []
        for match in CODE_BLOCK_REGEX.finditer(text):
            lang = match.group(1) or "txt"
            code = match.group(2).strip()
            blocks.append( (lang, code) )
        return blocks
    def safe_filename(dt, n, lang):
        dt_str = dt.strftime("%Y%m%d-%H%M")
        ext = ".py" if lang in ("python", "py") else ".txt"
        return f"{dt_str}-code-{n:04d}{ext}"
    CHAT_DIRS = [Path(JEMAI_HUB), Path(JEMAI_HUB, "chatgpt"), Path(JEMAI_HUB, "vertex")]
    dt = datetime.datetime.now()
    for chat_dir in CHAT_DIRS:
        if not chat_dir.exists(): continue
        for root, dirs, files in os.walk(chat_dir):
            for f in files:
                if f.endswith((".json", ".txt", ".md", ".html")):
                    try:
                        content = open(os.path.join(root, f), encoding="utf-8", errors="ignore").read()
                        blocks = extract_code_blocks(content)
                        moods = [guess_sentiment(content)]
                        n_found = 0
                        for lang, code in blocks:
                            fn = safe_filename(dt, n_found, lang)
                            path = OUT_DIR / fn
                            with open(path, "w", encoding="utf-8") as out:
                                out.write(code)
                            index_log.append({
                                "filename": str(path), "lang": lang, "source": str(f),
                                "dt": str(dt),
                                "sentiment": guess_sentiment(code),
                                "snippet": code[:80] + "..." if len(code)>80 else code
                            })
                            n_found += 1
                        master_log.append({
                            "chat_source": str(f),
                            "total_code_blocks": n_found,
                            "moods": moods,
                            "avg_sentiment": max(set(moods), key=moods.count) if moods else "neutral",
                        })
                    except Exception as e:
                        pass
    json.dump(index_log, open(INDEX_FILE,"w",encoding="utf-8"), indent=2)
    json.dump(master_log, open(MASTER_FILE,"w",encoding="utf-8"), indent=2)
    return f"Indexed {len(index_log)} code snippets."

register_plugin("davesort", davesort_run)

# === FLASK APP CONTINUES IN PART 2... ===

# === FLASK APP + WEB UI (continued) ===
from flask_socketio import SocketIO, emit
app = Flask(__name__)
socketio = SocketIO(app, async_mode="threading")
THEMES = {
    "WarmWinds": {
        "bg": "radial-gradient(circle at 30% 100%,#ffe8c7 0%,#eec08b 75%)",
        "color": "#4c2207"
    },
    "AIFuture": {
        "bg": "linear-gradient(135deg,#222b47 30%,#21ffe7 100%)",
        "color": "#f4f4f4"
    },
    "HackerDark": {
        "bg": "#151b26",
        "color": "#b4ffa7"
    }
}
AUDIO_DEVICES = ["Default", "Sonos Living", "Logitech USB", "NVIDIA HDMI", "Loopback", "Virtual Speaker"]
MIC_DEVICES = ["Default", "Blue Yeti", "Webcam Mic", "Wireless", "Virtual Mic"]

def render_main(theme="WarmWinds"):
    dev = device_info()
    cur_theme = THEMES.get(theme, THEMES["WarmWinds"])
    code_files = list_files(JEMAI_HUB)
    versions = [v[0] for v in list_versions()]
    plugins = list(PLUGIN_FUNCS.keys())
    ollama_models = dev.get("ollama_models", [])
    return render_template_string(f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <title>JEMAI AGI OS</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    html,body {{ margin:0;padding:0;min-height:100vh;width:100vw;
      font-family:'Segoe UI',Arial,sans-serif;
      background:{cur_theme['bg']}; color:{cur_theme['color']};overflow-x:hidden; }}
    .mainnav {{ background:#fff5;backdrop-filter:blur(12px);padding:14px 32px 8px 38px;font-size:1.21em;display:flex;gap:33px;align-items:center;box-shadow:0 6px 28px #2fd5c144; }}
    .mainnav .navbtn {{ background:none;border:none;color:{cur_theme['color']};font-size:1.13em;padding:9px 15px;margin-right:7px;cursor:pointer; }}
    .mainnav .navbtn.active {{ color:#2fd5c1;font-weight:700; }}
    .mainnav .logo {{ font-size:2.3em;font-weight:800;letter-spacing:0.08em;color:#2fd5c1;margin-right:22px; }}
    .theme-picker, .audio-picker, .mic-picker {{ margin-left:13px; }}
    .theme-opt {{ background:#fffa;border:none;font-size:1em;padding:4px 9px;cursor:pointer;border-radius:7px;margin-right:4px; }}
    .section {{ display:none; padding:2vw;}}
    .section.active {{ display:block; }}
    .button-main {{font-size:1.9em;background:linear-gradient(100deg,#2fd5c1 0,#21ffe7 90%);color:#142c2c;
      padding:27px 67px; border:none; border-radius:24px; cursor:pointer;box-shadow:0 6px 28px #2fd5c133;transition:box-shadow .2s,background .13s; margin:27px 0;}}
    .button-main:active {{background:#24bfb6;}}
    .file-tree {{background:#fff7;margin-top:14px;padding:12px;border-radius:13px;font-size:1.07em;color:#333;max-width:340px;overflow:auto;}}
    .code-preview {{background:#222c33;color:#e4e6e7;font-family:monospace;padding:13px;border-radius:9px;margin:8px 0;max-width:680px;overflow:auto;white-space:pre;}}
    .diff {{background:#272b2f;color:#fcf9c7;font-family:monospace;padding:13px;border-radius:9px;margin:8px 0;max-width:680px;overflow:auto;white-space:pre;}}
    .plugin-bar, .model-bar, .audio-bar, .mic-bar {{margin-top:18px;margin-bottom:10px;}}
    .chip {{display:inline-block;padding:2px 11px;border-radius:19px;font-size:1em;background:#b4fbd6;color:#163f3a;margin:2px 7px 2px 0;}}
    .file-opt {{ cursor:pointer;color:#24bfb6; }}
    .file-opt:hover { color:#125050;font-weight:700; }
    .editor {{width:92vw;height:67vh;margin:21px 0;background:#191d23;border-radius:12px;}}
    iframe.vscode-iframe {{width:100%;height:80vh;border-radius:12px;border:none;box-shadow:0 3px 22px #24576b55;}}
    .sidebar {{background:#151d25e8;position:fixed;top:0;right:0;width:360px;height:100vh;padding:27px;z-index:999;box-shadow:-8px 0 28px #3ddad644;overflow-y:auto;}}
    .rightbar-tile {{margin-bottom:20px;}}
    .rc-botbar {{position:fixed;bottom:0;left:0;width:100vw;padding:10px 0 9px 40px;background:#e0e4e85a;z-index:90;box-shadow:0 0 38px #2222;}}
    .groupchat-btn {background:#ffeebd;border:none;color:#111;font-size:1.17em;padding:7px 28px;border-radius:18px;cursor:pointer;margin-right:18px;}
    .model-opt {background:#ffe1;border:none;color:#1c5f53;font-size:1em;padding:5px 13px;border-radius:11px;cursor:pointer;margin-right:8px;}
  </style>
  <script>
    let curSection = "chat", theme = "{theme}", audio = "Default", mic = "Default";
    let allSections = ["chat","explorer","vscode","versions","wiki","settings","plugins"];
    function showSection(s) {{
        allSections.forEach(sec=>{{document.getElementById("sec_"+sec).classList.remove("active");}});
        document.getElementById("sec_"+s).classList.add("active");
        curSection=s;
        if(s==="explorer") {{ loadFileTree(); }}
        if(s==="versions") {{ loadVersions(); }}
        if(s==="plugins") {{ loadPlugins(); }}
        if(s==="wiki") {{ loadWiki(); }}
    }}
    function setTheme(t) {{
        fetch('/api/theme/'+t).then(()=>location.reload());
    }}
    function setAudio(a) {{ fetch('/api/audio/'+a).then(()=>location.reload());}}
    function setMic(m) {{ fetch('/api/mic/'+m).then(()=>location.reload());}}
    function groupChat() {{ document.getElementById("groupchatbox").innerHTML = "Summoning models..."; fetch('/api/groupchat').then(r=>r.json()).then(j=>{document.getElementById("groupchatbox").innerHTML=j.resp;});}}
    function loadFileTree() {{
        fetch('/api/files').then(r=>r.json()).then(list=>{
          let d=document.getElementById('filetree');
          d.innerHTML='';
          list.forEach(f=>{
            let el=document.createElement('div');
            el.className='file-opt';
            el.innerText=f;
            el.onclick=()=>viewFile(f);
            d.appendChild(el);
          });
        });
    }}
    function viewFile(f) {{
        fetch('/api/file/'+encodeURIComponent(f)).then(r=>r.json()).then(j=>{
            document.getElementById('fileview').innerHTML='<div class="code-preview">'+(j.code||'[empty]')+'</div>';
        });
    }}
    function loadVersions() {{
        fetch('/api/versions').then(r=>r.json()).then(list=>{
          let d=document.getElementById('verlist');
          d.innerHTML='';
          list.forEach((v,i)=>{
            let el=document.createElement('div');
            el.className='file-opt';
            el.innerText=v;
            el.onclick=()=>viewVersion(v);
            d.appendChild(el);
          });
        });
    }}
    function viewVersion(f) {{
        fetch('/api/version/'+encodeURIComponent(f)).then(r=>r.json()).then(j=>{
            document.getElementById('verview').innerHTML='<div class="code-preview">'+(j.code||'[empty]')+'</div>';
        });
    }}
    function loadPlugins() {{
        fetch('/api/plugins').then(r=>r.json()).then(list=>{
          let d=document.getElementById('pluginlist');
          d.innerHTML='';
          list.forEach((p,i)=>{
            let el=document.createElement('div');
            el.className='chip';
            el.innerText=p;
            el.onclick=()=>runPlugin(p);
            d.appendChild(el);
          });
        });
    }}
    function runPlugin(p) {{
        fetch('/api/plugin/'+p).then(r=>r.json()).then(j=>{
            document.getElementById('pluginoutput').innerHTML='<div class="code-preview">'+(j.result||'No output')+'</div>';
        });
    }}
    function loadWiki() {{
        fetch('/api/wiki').then(r=>r.json()).then(j=>{
            document.getElementById('wikiview').innerHTML='<textarea style="width:98%;height:55vh;font-size:1.1em;background:#ffeebd;color:#363202;border-radius:11px;" id="wiki_edit">'+j.content+'</textarea>';
        });
    }}
    function saveWiki() {{
        let v=document.getElementById('wiki_edit').value;
        fetch('/api/wiki',{method:"POST",headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{content:v}})})
        .then(()=>alert("Saved!"));
    }}
    function groupChatSend() {{
        let q = document.getElementById("groupchat_inp").value;
        fetch('/api/groupchat',{method:"POST",headers:{{'Content-Type':'application/json'}},body:JSON.stringify({q:q})})
        .then(r=>r.json()).then(j=>{
            document.getElementById("groupchatbox").innerHTML=j.resp;
        });
    }}
    // Voice: uses browser speech
    function speak(txt) {{
        let utter = new SpeechSynthesisUtterance(txt);
        utter.lang = "en-US";
        window.speechSynthesis.speak(utter);
    }}
    function listen() {{
        if(!('webkitSpeechRecognition' in window)){ alert("Not supported"); return;}
        let rec = new webkitSpeechRecognition();
        rec.lang = 'en-US'; rec.onresult=function(e){{if(e.results.length)document.getElementById('chat_inp').value = e.results[0][0].transcript;}};
        rec.start();
    }}
    // VSCode iframe: localhost:8443 by default
    function loadVSCode() {{
        document.getElementById('vscodeiframe').src = "http://localhost:8443";
    }}
    window.onload = function() {{
      showSection('chat');
      loadVSCode();
    }};
  </script>
</head>
<body>
<div class="mainnav">
  <span class="logo">JEMAI</span>
  <button class="navbtn active" onclick="showSection('chat')">Chat</button>
  <button class="navbtn" onclick="showSection('explorer')">Explorer</button>
  <button class="navbtn" onclick="showSection('vscode')">VSCode</button>
  <button class="navbtn" onclick="showSection('versions')">Versions</button>
  <button class="navbtn" onclick="showSection('wiki')">Wiki</button>
  <button class="navbtn" onclick="showSection('plugins')">Plugins</button>
  <button class="navbtn" onclick="showSection('settings')">Settings</button>
  <span class="theme-picker">
    Theme: <select onchange="setTheme(this.value)">{''.join([f'<option{" selected" if k==theme else ""}>{k}</option>' for k in THEMES.keys()])}</select>
  </span>
  <span class="audio-picker">
    Audio: <select onchange="setAudio(this.value)">{''.join([f'<option>{" selected" if a=="Default" else ""}>{a}</option>' for a in AUDIO_DEVICES])}</select>
  </span>
  <span class="mic-picker">
    Mic: <select onchange="setMic(this.value)">{''.join([f'<option>{" selected" if m=="Default" else ""}>{m}</option>' for m in MIC_DEVICES])}</select>
  </span>
</div>
<!-- Main Sections -->
<div id="sec_chat" class="section active">
  <div style="margin-top:33px;">
    <button class="button-main" onclick="listen()">🎤 Talk to JEMAI</button>
    <input id="chat_inp" style="width:47vw;padding:12px 19px;font-size:1.22em;margin-left:18px;border-radius:9px;" placeholder="Type or say something..." />
    <button onclick="fetch('/api/chat',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{q:document.getElementById('chat_inp').value}})}}).then(r=>r.json()).then(j=>{{speak(j.resp||'');alert(j.resp);}})">Send</button>
  </div>
  <div style="margin:15px 0;">
    <div id="chatlog" style="background:#f8fffae6;color:#262b38;border-radius:12px;min-height:90px;max-width:1100px;padding:24px;"></div>
    <div style="margin-top:30px;">
      <button class="groupchat-btn" onclick="groupChat()">👥 Group Chat (Multiple Models)</button>
      <input id="groupchat_inp" placeholder="Message for all models..." style="width:340px;padding:9px 14px;border-radius:9px;" />
      <button onclick="groupChatSend()">Send</button>
      <div id="groupchatbox" style="margin:9px 0 0 0;background:#eafcf5;padding:12px 14px;border-radius:11px;"></div>
    </div>
  </div>
</div>
<div id="sec_explorer" class="section">
  <h2>File Explorer</h2>
  <div class="file-tree" id="filetree"></div>
  <div id="fileview"></div>
  <input type="file" id="file_upload" multiple onchange="uploadFiles()" />
  <script>
    function uploadFiles() {
      let files = document.getElementById('file_upload').files;
      for(let i=0;i<files.length;i++){
        let fd = new FormData();
        fd.append("file", files[i]);
        fetch("/api/upload", {method:"POST",body:fd}).then(()=>loadFileTree());
      }
    }
  </script>
</div>
<div id="sec_vscode" class="section">
  <h2>VSCode Embedded</h2>
  <iframe id="vscodeiframe" class="vscode-iframe" src="http://localhost:8443"></iframe>
</div>
<div id="sec_versions" class="section">
  <h2>Version History & Rollback</h2>
  <div id="verlist"></div>
  <div id="verview"></div>
</div>
<div id="sec_wiki" class="section">
  <h2>JEMAI OS Wiki & Notes</h2>
  <div id="wikiview"></div>
  <button onclick="saveWiki()" style="margin-top:9px;">Save Wiki</button>
</div>
<div id="sec_plugins" class="section">
  <h2>Plugin Management</h2>
  <div class="plugin-bar" id="pluginlist"></div>
  <div id="pluginoutput"></div>
</div>
<div id="sec_settings" class="section">
  <h2>Settings & Device Manager</h2>
  <div class="rightbar-tile">
    <b>System Info:</b> Host: <b>{dev['hostname']}</b> | IP: {dev['ip']} | OS: {dev['os_version']}<br>
    CPU: {dev['cpu']}% | RAM: {dev['ram']}% | Disk: {dev['disk']}%<br>
    Ollama Models: {', '.join(dev['ollama_models'])}<br>
    GPU: {', '.join(dev['gpus']) if dev['gpus'] else "None"}<br>
    Plugins: {', '.join(plugins)}<br>
  </div>
  <div class="rightbar-tile">
    <b>Audio Out:</b> <select onchange="setAudio(this.value)">{''.join([f'<option>{" selected" if a=="Default" else ""}>{a}</option>' for a in AUDIO_DEVICES])}</select>
    <b>Mic In:</b> <select onchange="setMic(this.value)">{''.join([f'<option>{" selected" if m=="Default" else ""}>{m}</option>' for m in MIC_DEVICES])}</select>
  </div>
  <div class="rightbar-tile">
    <button onclick="fetch('/api/reboot')">Reboot</button>
    <button onclick="fetch('/api/update')">Update</button>
  </div>
  <div>
    <b>Home Assistant Devices:</b>
    <div id="ha_devices"></div>
    <button onclick="fetch('/api/ha/devices').then(r=>r.json()).then(j=>{{document.getElementById('ha_devices').innerText=JSON.stringify(j,null,2)}})">Refresh HA Devices</button>
  </div>
</div>
<div class="footer" style="margin-top:22px;">JEMAI AGI OS &copy; {datetime.datetime.now().year} &mdash; <a href="#" onclick="location.reload()">Refresh</a></div>
</body>
</html>
""")

# === CONTINUE TO PART 3 ===
#   - All routes (/api/theme, /api/audio, /api/mic, /api/file, /api/version, /api/rollback, /api/upload, /api/chat, /api/groupchat, /api/wiki, /api/ha, etc)
#   - VSCode, Overlay, Plugins, ChromaDB/RAG, Home Assistant, Audio/Mic selection, Mood, Master changelog, etc.
#   - All backend logic and "baked-in" integrations.
#   - No suggestions, only code.
# 
# >>> Reply: **Continue generating**

from flask import request, jsonify, send_from_directory
import difflib
import uuid

THEME_FILE = os.path.join(JEMAI_HUB, "theme.txt")
AUDIO_FILE = os.path.join(JEMAI_HUB, "audio.txt")
MIC_FILE = os.path.join(JEMAI_HUB, "mic.txt")
WIKI_FILE = os.path.join(JEMAI_HUB, "jemai_wiki.md")
CHANGELOG_FILE = os.path.join(JEMAI_HUB, "jemai_changelog.json")
ROLLBACK_PORT = 18801

# ======== SETTINGS STATE ========
def get_setting(path, default=""):
    try:
        if os.path.exists(path): return open(path, encoding="utf-8").read().strip()
    except: pass
    return default

def set_setting(path, value):
    try:
        with open(path, "w", encoding="utf-8") as f: f.write(str(value))
        return True
    except: return False

@app.route("/api/theme/<theme>")
def api_theme(theme):
    if theme not in THEMES: return "Invalid", 400
    set_setting(THEME_FILE, theme)
    return "ok"

@app.route("/api/audio/<audio>")
def api_audio(audio):
    if audio not in AUDIO_DEVICES: return "Invalid", 400
    set_setting(AUDIO_FILE, audio)
    return "ok"

@app.route("/api/mic/<mic>")
def api_mic(mic):
    if mic not in MIC_DEVICES: return "Invalid", 400
    set_setting(MIC_FILE, mic)
    return "ok"

# ======== FILE EXPLORER, VERSIONS, WIKI ========
def list_versions():
    ver_dir = JEMAI_HUB
    files = [f for f in os.listdir(ver_dir) if "-jemai.py" in f]
    files.sort()
    out = []
    for fn in files:
        path = os.path.join(ver_dir, fn)
        ts = os.path.getmtime(path)
        out.append((fn, ts))
    return sorted(out, key=lambda x: x[1], reverse=True)

@app.route("/api/versions")
def api_versions():
    return jsonify([v[0] for v in list_versions()])

@app.route("/api/version/<vfile>")
def api_version(vfile):
    path = os.path.join(JEMAI_HUB, vfile)
    if not os.path.exists(path): return jsonify({"code": "[File missing]"})
    code = open(path, encoding="utf-8").read()
    return jsonify({"code": code})

@app.route("/api/file/<path:fname>")
def api_file(fname):
    fpath = os.path.join(JEMAI_HUB, fname)
    if not os.path.exists(fpath): return jsonify({"code":"[File missing]"})
    code = open(fpath, encoding="utf-8", errors="ignore").read()
    return jsonify({"code": code})

@app.route("/api/upload", methods=["POST"])
def api_upload():
    f = request.files['file']
    fname = f.filename
    savepath = os.path.join(JEMAI_HUB, fname)
    f.save(savepath)
    return "ok"

# ==== VERSION ROLLBACK, DIFF, LIVE PREVIEW ====
@app.route("/api/rollback/<vfile>")
def api_rollback(vfile):
    vpath = os.path.join(JEMAI_HUB, vfile)
    if not os.path.exists(vpath): return "Missing file", 404
    dest = os.path.join(JEMAI_HUB, "jemai.py")
    shutil.copy2(vpath, dest)
    add_changelog_entry(f"Rolled back to {vfile}")
    return "Rolled back"

@app.route("/api/diff/<vfile1>/<vfile2>")
def api_diff(vfile1, vfile2):
    p1 = os.path.join(JEMAI_HUB, vfile1)
    p2 = os.path.join(JEMAI_HUB, vfile2)
    if not os.path.exists(p1) or not os.path.exists(p2): return jsonify({"diff": "[File missing]"})
    a = open(p1, encoding="utf-8").read().splitlines()
    b = open(p2, encoding="utf-8").read().splitlines()
    diff = "\n".join(difflib.unified_diff(a, b, fromfile=vfile1, tofile=vfile2, lineterm=""))
    return jsonify({"diff": diff})

@app.route("/api/wiki", methods=["GET","POST"])
def api_wiki():
    if request.method=="POST":
        content = (request.json or {}).get("content","")
        with open(WIKI_FILE,"w",encoding="utf-8") as f: f.write(content)
        add_changelog_entry("Wiki updated")
        return "ok"
    if not os.path.exists(WIKI_FILE): open(WIKI_FILE,"w").write("# JEMAI Wiki\n")
    return jsonify({"content":open(WIKI_FILE,encoding="utf-8").read()})

# ==== CHANGELOG ====
def add_changelog_entry(event, user="user", mood=None):
    log = []
    if os.path.exists(CHANGELOG_FILE):
        try: log = json.load(open(CHANGELOG_FILE,encoding="utf-8"))
        except: log = []
    entry = {
        "id": str(uuid.uuid4()),
        "event": event,
        "time": datetime.datetime.now().isoformat(),
        "user": user,
        "mood": mood or analyze_last_mood(),
    }
    log.append(entry)
    with open(CHANGELOG_FILE,"w",encoding="utf-8") as f:
        json.dump(log, f, indent=2)

@app.route("/api/changelog")
def api_changelog():
    if not os.path.exists(CHANGELOG_FILE): return jsonify([])
    log = json.load(open(CHANGELOG_FILE,encoding="utf-8"))
    return jsonify(log[-40:])

# ==== SIMPLE MOOD DETECTION ====
def analyze_last_mood():
    try:
        lines = open(os.path.join(JEMAI_HUB,"jemai_wiki.md"),encoding="utf-8").read().splitlines()[-20:]
        s = " ".join(lines)
        if "happy" in s or "excited" in s: return "happy"
        if "pissed" in s or "angry" in s: return "angry"
        if "tired" in s or "sleep" in s: return "tired"
        if "lazy" in s: return "lazy"
        if "sad" in s: return "sad"
        return "neutral"
    except: return "neutral"

# ==== GROUP CHAT (MULTI-MODEL) ====
@app.route("/api/groupchat", methods=["GET","POST"])
def api_groupchat():
    models = ollama_list_models()
    if not models: return jsonify({"resp":"[No models available]"})
    history = []
    if request.method=="POST":
        q = (request.json or {}).get("q","")
        responses = []
        for m in models:
            try:
                import requests
                r = requests.post("http://localhost:11434/api/generate",
                    json={"model":m,"prompt":q,"stream":False},timeout=60)
                if r.ok:
                    resp = r.json().get("response","")
                    responses.append(f"<b>{m}:</b> {resp}")
            except: continue
        out = "<br><hr>".join(responses)
        add_changelog_entry(f"Group chat to models: {', '.join(models)}")
        return jsonify({"resp":out})
    # GET: show current models
    return jsonify({"resp":"Models: "+"<br>".join(models)})

# ==== PLUGINS ====
@app.route("/api/plugins")
def api_plugins2():
    return jsonify(list(PLUGIN_FUNCS.keys()))

@app.route("/api/plugin/<name>")
def api_plugin2(name):
    if name in PLUGIN_FUNCS:
        try: return jsonify({"result": PLUGIN_FUNCS[name]()})
        except Exception as e: return jsonify({"result": f"[Error] {e}"})
    return jsonify({"result":"Not found"})

# ==== FILE UPLOAD API ====
@app.route("/api/files", methods=["GET"])
def api_files2():
    files = []
    for root, dirs, fs in os.walk(JEMAI_HUB):
        for f in fs:
            files.append(os.path.relpath(os.path.join(root, f), JEMAI_HUB))
    return jsonify(files)

# ==== HOME ASSISTANT (SONOS, LIGHTS, ETC) ====
def get_ha_url():
    return os.environ.get("HOME_ASSISTANT_URL") or "http://homeassistant.local:8123"
def get_ha_token():
    t = os.environ.get("HOME_ASSISTANT_TOKEN") or ""
    if not t and os.path.exists(os.path.join(JEMAI_HUB,"ha_token.txt")):
        t = open(os.path.join(JEMAI_HUB,"ha_token.txt")).read().strip()
    return t

@app.route("/api/ha/devices")
def api_ha_devices():
    url = get_ha_url()
    token = get_ha_token()
    if not token: return jsonify({"error":"No HA token configured."})
    try:
        import requests
        r = requests.get(f"{url}/api/states",headers={"Authorization":f"Bearer {token}"})
        if r.ok:
            devs = r.json()
            out = [{"id":d["entity_id"],"name":d.get("attributes",{}).get("friendly_name",d["entity_id"])} for d in devs]
            return jsonify(out)
        return jsonify({"error":f"HTTP {r.status_code}"})
    except Exception as e:
        return jsonify({"error":str(e)})

@app.route("/api/ha/call", methods=["POST"])
def api_ha_call():
    url = get_ha_url()
    token = get_ha_token()
    data = request.json or {}
    domain = data.get("domain","light")
    service = data.get("service","toggle")
    entity = data.get("entity_id","")
    try:
        import requests
        r = requests.post(f"{url}/api/services/{domain}/{service}",
                          headers={"Authorization":f"Bearer {token}"},
                          json={"entity_id":entity})
        return jsonify({"resp": r.text})
    except Exception as e:
        return jsonify({"error":str(e)})

# ==== CHROMADB & RAG (BAKED IN) ====
CHROMA_DIR = os.path.join(JEMAI_HUB,"chromadb")
def chromadb_add_doc(text, meta=None):
    # Minimal vector DB using file per chunk (mock: just save file, real: use Chroma)
    os.makedirs(CHROMA_DIR, exist_ok=True)
    fname = os.path.join(CHROMA_DIR, f"chunk_{uuid.uuid4().hex}.txt")
    with open(fname,"w",encoding="utf-8") as f: f.write(text)
    # meta ignored here for simplicity

def chromadb_query(q, limit=3):
    hits = []
    if not os.path.exists(CHROMA_DIR): return []
    for fn in os.listdir(CHROMA_DIR):
        path = os.path.join(CHROMA_DIR, fn)
        txt = open(path,encoding="utf-8").read()
        if q.lower() in txt.lower():
            hits.append(txt[:200])
        if len(hits)>=limit: break
    return hits

@app.route("/api/rag/search")
def api_rag_search():
    q = request.args.get("q","")
    results = chromadb_query(q, 6)
    return jsonify(results)

@app.route("/api/rag/add", methods=["POST"])
def api_rag_add():
    t = (request.json or {}).get("text","")
    chromadb_add_doc(t)
    return "ok"

# ==== VSCode IFRAME & LIVE EDITOR ====
@app.route("/api/vscodeproxy/<path:sub>")
def api_vscode_proxy(sub):
    # Basic reverse proxy for VSCode
    import requests
    url = f"http://localhost:8443/{sub}"
    try:
        resp = requests.get(url)
        return resp.content, resp.status_code, resp.headers.items()
    except Exception as e:
        return str(e), 502

# ==== SYSTEM COMMANDS (REBOOT/UPDATE) ====
@app.route("/api/reboot")
def api_reboot():
    add_changelog_entry("System reboot requested")
    if IS_WINDOWS:
        os.system("shutdown /r /t 1")
    else:
        os.system("reboot")
    return "Rebooting..."

@app.route("/api/update")
def api_update():
    add_changelog_entry("System update triggered")
    # Stub for git pull or similar
    return "Update (stub)"

# ==== AUTOINSTALL (FLASK, SOCKETIO, ETC) ====
def ensure_requirements():
    reqs = ["flask", "flask_socketio", "psutil"]
    try:
        import pip
        for r in reqs:
            try: __import__(r)
            except ImportError: os.system(f"{sys.executable} -m pip install {r}")
    except: pass
ensure_requirements()

# ==== MAIN ENTRY ====
if __name__ == "__main__":
    # Save current version snapshot if not yet present
    dt = datetime.datetime.now().strftime("%d%m%Y-%H%M")
    snap_path = os.path.join(JEMAI_HUB, f"{dt}-jemai.py")
    if not os.path.exists(snap_path):
        shutil.copy2(__file__, snap_path)
        add_changelog_entry(f"Snapshot {dt}-jemai.py")
    # Start SocketIO server for realtime UI
    socketio.run(app, host="0.0.0.0", port=8181, debug=False)
