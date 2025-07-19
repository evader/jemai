import os, sys, time, datetime, threading, platform, json, psutil, socket, sqlite3, base64, random, shutil, subprocess, difflib, html
from flask import Flask, request, jsonify, render_template_string, send_from_directory, redirect
from pathlib import Path

IS_WINDOWS = platform.system() == "Windows"
HOME = str(Path.home())
JEMAI_HUB = os.path.join(HOME, "jemai_hub")
PLUGINS_DIR = os.path.join(JEMAI_HUB, "plugins")
VERSIONS_DIR = os.path.join(JEMAI_HUB, "OLD", "Versions")
SQLITE_PATH = os.path.join(JEMAI_HUB, "jemai_hub.sqlite3")
WIKI_MD = os.path.join(VERSIONS_DIR, "JEMAI_WIKI.md")
os.makedirs(JEMAI_HUB, exist_ok=True)
os.makedirs(PLUGINS_DIR, exist_ok=True)
os.makedirs(VERSIONS_DIR, exist_ok=True)

# ==== ChromaDB baked in ====
try:
    import chromadb
    CHROMA_CLIENT = chromadb.PersistentClient(os.path.join(JEMAI_HUB, "chromadb"))
    CHROMA_COLL = CHROMA_CLIENT.get_or_create_collection("jemai_docs")
except Exception as e:
    CHROMA_CLIENT = CHROMA_COLL = None

# ==== Plugins ====
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

# ==== Utils ====
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

def save_version_copy():
    dt = datetime.datetime.now().strftime("%d%m%Y-%H%M-%S")
    base = os.path.join(VERSIONS_DIR, f"{dt}-jemai.py")
    shutil.copy2(__file__, base)

def diff_codes(codeA, codeB):
    a = codeA.splitlines()
    b = codeB.splitlines()
    return difflib.HtmlDiff(tabsize=2).make_table(a, b, 'Old', 'New', context=True, numlines=5)

# ==== Flask App ====
app = Flask(__name__)

# Main Dashboard, Chat, Code, Explorer, Plugins, etc
@app.route("/")
def main_ui():
    # ... (dashboard HTML same as before, truncated for brevity)
    # Add nav link to /wiki
    year = datetime.datetime.now().year
    return render_template_string("""
<!DOCTYPE html>
<html lang="en"><head><title>JEMAI AGI OS</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs/editor/editor.main.min.css" />
<style>
html,body{margin:0;padding:0;min-height:100vh;width:100vw;font-family:'Segoe UI',Arial,sans-serif;background:radial-gradient(circle at 30% 100%,#2d2c44 0%,#131319 75%) no-repeat;color:#fff;overflow-x:hidden;}
.navbar{width:100%;background:#262d36aa;padding:10px 16px;display:flex;gap:27px;align-items:center;}
.navbar a{color:#9effff;font-size:1.09em;font-weight:600;text-decoration:none;padding:3px 17px;border-radius:8px;}
.navbar a:hover{background:#252f44b0;}
.glass{background:rgba(38,43,57,0.7);border-radius:28px;box-shadow:0 7px 48px #3ddad65b;padding:36px 28px 18px 28px;margin:18px 1vw 30px 1vw;width:98vw;max-width:1900px;}
.footer{margin-top:18px;color:#6edac8;font-size:1em;text-align:center;opacity:0.83;border-top:1px solid #235a42;padding-top:10px;}
</style>
<script>
function navto(a){location=a;}
</script>
</head>
<body>
<div class="navbar">
  <a href="/" style="color:#eaffaf">Dashboard</a>
  <a href="/wiki">Changelog/Wiki</a>
  <a href="/editor">Editor</a>
  <a href="/explorer">Explorer</a>
  <a href="/settings">Settings</a>
</div>
<div class="glass">
  <div style="font-size:2.1em;margin-bottom:16px;"><b>JEMAI <span style="font-size:.6em;color:#8fffff;font-weight:400;">AGI OS</span></b></div>
  <div style="margin-bottom:18px;font-size:1.18em;">
    Welcome to the unified AGI OS. Everything in one place: chat, group chat, code, memory, file explorer, plugins, RAG, VSCode, rollback, themes, audio, and more.
  </div>
  <div style="margin:0 0 19px 0">
    <button onclick="navto('/chat')" style="padding:17px 40px;font-size:1.45em;background:#2fd5c1;color:#122c2b;border:none;border-radius:15px;font-weight:700;box-shadow:0 4px 26px #3ddad633;">Open JEMAI Chat/OS</button>
  </div>
  <hr>
  <div style="margin:22px 0;">
    <b>Quick Links:</b>
    <a href="/wiki">Changelog & Version Rollback</a> | 
    <a href="/editor">VSCode Web Editor</a> |
    <a href="/explorer">File Explorer</a> |
    <a href="/settings">Settings/Audio</a>
  </div>
</div>
<div class="footer">
  <span>JEMAI AGI OS &copy; {{year}} | <a href="#" onclick="location.reload()">Refresh</a></span>
</div>
</body></html>
""", year=year)

# === Explorer ===
@app.route("/explorer")
def explorer():
    files = list_files()
    return render_template_string("""
    <html><body style='background:#262d36;color:#fff;font-family:monospace;padding:34px;'>
      <h2>JEMAI File Explorer</h2>
      <div>JEMAI Hub Files (click to view/edit):</div>
      <ul>
      {% for f in files %}
        <li><a href='/editor?file={{f}}'>{{f}}</a></li>
      {% endfor %}
      </ul>
      <a href='/' style='color:#aef;'>Back to Dashboard</a>
    </body></html>
    """, files=files)

# === Wiki/Changelog/Version Rollback ===
@app.route("/wiki")
def wiki_home():
    vers = [f for f in sorted(os.listdir(VERSIONS_DIR)) if f.endswith(".py")]
    md = open(WIKI_MD, encoding="utf-8").read() if os.path.exists(WIKI_MD) else "# JEMAI WIKI\n\n"
    return render_template_string("""
    <html>
    <head>
      <title>JEMAI Wiki / Changelog</title>
      <style>body{background:#191d28;color:#ffd;font-family:Segoe UI,Arial;margin:0;padding:0;} .main{max-width:1220px;margin:20px auto;background:#262d36;border-radius:16px;padding:25px 30px;} h1,h2{color:#ffd06d;} textarea{width:98%;height:250px;margin:7px 0;background:#262d36;color:#ffd;font-family:monospace;} .verslist{font-size:1.11em;margin:12px 0;}</style>
      <script>
      function loadver(fn){fetch('/viewver?fn='+encodeURIComponent(fn)).then(r=>r.json()).then(j=>{document.getElementById('preview').innerHTML=j.code;});}
      function showdiff(a,b){fetch('/diffver?old='+encodeURIComponent(a)+'&new='+encodeURIComponent(b)).then(r=>r.json()).then(j=>{document.getElementById('preview').innerHTML=j.diff;});}
      function rollback(fn){if(confirm('Rollback to '+fn+'?')){fetch('/rollbackver?fn='+encodeURIComponent(fn)).then(r=>r.json()).then(j=>alert(j.msg));}}
      function savewiki(){let md=document.getElementById('wikiedit').value;fetch('/savewiki',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({md})}).then(r=>r.json()).then(j=>alert(j.msg));}
      </script>
    </head>
    <body>
      <div class="main">
        <h1>JEMAI Wiki / Changelog</h1>
        <textarea id="wikiedit">{{md}}</textarea><br>
        <button onclick="savewiki()">Save Changelog</button>
        <hr>
        <h2>Version History</h2>
        <div class="verslist">
        {% for v in vers %}
          <div>
            <a href="javascript:loadver('{{v}}')">{{v}}</a>
            <button onclick="showdiff('{{vers[0]}}','{{v}}')">Diff from first</button>
            <button onclick="showdiff('{{v}}','{{vers[-1]}}')">Diff to latest</button>
            <button onclick="rollback('{{v}}')">Rollback</button>
          </div>
        {% endfor %}
        </div>
        <div id="preview" style="margin:21px 0;"></div>
        <hr>
        <i>All versions in {{VERSIONS_DIR}}. Rollback = overwrite jemai.py.</i>
      </div>
    </body></html>
    """, vers=vers, md=md, VERSIONS_DIR=VERSIONS_DIR)

@app.route("/viewver")
def api_viewver():
    fn = request.args.get("fn")
    code = open(os.path.join(VERSIONS_DIR, fn), encoding="utf-8").read()
    code_html = "<pre style='background:#222;color:#e7ffb2;font-size:.98em;padding:6px;border-radius:6px;'>%s</pre>" % html.escape(code)
    return jsonify({"code": code_html})

@app.route("/diffver")
def api_diffver():
    old = request.args.get("old")
    new = request.args.get("new")
    codeA = open(os.path.join(VERSIONS_DIR, old), encoding="utf-8").read()
    codeB = open(os.path.join(VERSIONS_DIR, new), encoding="utf-8").read()
    return jsonify({"diff": diff_codes(codeA, codeB)})

@app.route("/rollbackver")
def api_rollbackver():
    fn = request.args.get("fn")
    shutil.copy2(os.path.join(VERSIONS_DIR, fn), os.path.join(JEMAI_HUB, "jemai.py"))
    return jsonify({"msg": f"Rolled back to {fn}!"})

@app.route("/savewiki", methods=["POST"])
def api_savewiki():
    data = request.json
    with open(WIKI_MD, "w", encoding="utf-8") as f:
        f.write(data.get("md", ""))
    return jsonify({"msg":"Changelog saved!"})

# === VSCode in iframe ===
@app.route("/editor")
def code_editor():
    file = request.args.get("file", "jemai.py")
    code = open(os.path.join(JEMAI_HUB, file), encoding="utf-8").read() if os.path.exists(os.path.join(JEMAI_HUB, file)) else ""
    return f"""
    <html><body style='background:#191d28;color:#f9f9c9;font-family:monospace;padding:44px;'>
    <h2>VSCode Web Editor (beta, file: {file})</h2>
    <textarea style='width:99vw;height:69vh;font-size:1.07em;'>{code}</textarea>
    <br><a href='/' style='color:#aef;margin-top:14px;display:inline-block;'>Back to AGI OS</a>
    </body></html>
    """

# === File API ===
@app.route("/api/files")
def api_files(): return jsonify(list_files())

# === RAG: Live ChromaDB upload/import ===
@app.route("/api/rag/import", methods=["POST"])
def api_rag_import():
    # Drag & drop or select file to import to ChromaDB
    if not CHROMA_COLL: return jsonify({"error": "ChromaDB unavailable"})
    f = request.files['file']
    content = f.read().decode("utf-8", errors="ignore")
    CHROMA_COLL.add(documents=[content], metadatas=[{"filename":f.filename}], ids=[str(random.randint(1000,9999))+f.filename])
    return jsonify({"msg":f"File '{f.filename}' imported to RAG."})

@app.route("/api/rag/search")
def api_rag_search():
    q = request.args.get("q","")
    if not CHROMA_COLL: return jsonify({"results":[]})
    results = CHROMA_COLL.query(query_texts=[q], n_results=4)
    return jsonify({"results":results.get("documents",[[]])[0]})

# (Add more as needed...)

# === Main Runner ===
if __name__ == "__main__":
    save_version_copy()
    if not os.path.exists(WIKI_MD):
        with open(WIKI_MD,"w",encoding="utf-8") as f: f.write("# JEMAI WIKI\n\n")
    app.run("0.0.0.0", 8181, debug=True)
