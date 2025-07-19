import os, sys, platform, subprocess, threading, datetime, json, glob, shutil, difflib
from flask import Flask, request, jsonify, render_template_string
import psutil

# ====================== GLOBALS & DIRECTORIES ======================
IS_WINDOWS = platform.system() == "Windows"
JEMAI_HUB = os.path.expanduser("~/jemai_hub") if not IS_WINDOWS else "C:/jemai_hub"
os.makedirs(JEMAI_HUB, exist_ok=True)
VERSIONS_DIR = os.path.join(JEMAI_HUB, ".jemai_versions")
os.makedirs(VERSIONS_DIR, exist_ok=True)
PLUGINS_DIR = os.path.join(JEMAI_HUB, "plugins")
os.makedirs(PLUGINS_DIR, exist_ok=True)
ACCESS_ERRORS = []

# ====================== FULL SYSTEM ACCESS CHECK ===================
def check_access():
    global ACCESS_ERRORS
    ACCESS_ERRORS = []
    try:
        test_file = os.path.join(JEMAI_HUB, "jemai_access_test.txt")
        with open(test_file, "w") as f: f.write("test")
        os.remove(test_file)
    except Exception as e:
        ACCESS_ERRORS.append(f"FS: {e}")
    try:
        out = subprocess.check_output("echo JEMAI_SHELL_OK", shell=True)
        if b"JEMAI_SHELL_OK" not in out: ACCESS_ERRORS.append("Shell not OK")
    except Exception as e:
        ACCESS_ERRORS.append(f"Shell: {e}")

# ====================== CORE COMMAND INTERPRETER ===================
def interpret_and_act(cmd):
    lcmd = cmd.strip().lower()
    # Directory listing
    if lcmd in ["dir", "ls", "list files"]:
        try:
            files = "\n".join(os.listdir(JEMAI_HUB))
            return f"Files in {JEMAI_HUB}:\n{files}"
        except Exception as e:
            return f"[DIR ERROR] {e}"
    if lcmd.startswith(("dir ", "ls ")):
        path = cmd.split(" ", 1)[1] if " " in cmd else JEMAI_HUB
        try:
            files = "\n".join(os.listdir(os.path.expanduser(path)))
            return f"Files in {path}:\n{files}"
        except Exception as e:
            return f"[DIR ERROR @ {path}] {e}"
    # Show file contents
    if lcmd.startswith(("cat ","type ")):
        fname = cmd.split(" ",1)[1] if " " in cmd else ""
        path = os.path.join(JEMAI_HUB, fname)
        if not os.path.exists(path): return f"[ERROR] File not found: {fname}"
        try:
            with open(path,encoding="utf-8",errors="replace") as f: return f.read()
        except Exception as e: return f"[READ ERROR] {e}"
    # Remove file
    if lcmd.startswith("del "):
        fname = cmd.split(" ",1)[1]
        path = os.path.join(JEMAI_HUB, fname)
        try: os.remove(path); return f"Deleted: {fname}"
        except Exception as e: return f"[DELETE ERROR] {e}"
    # Write file
    if lcmd.startswith("write "):
        parts = cmd.split(" ",2)
        if len(parts)<3: return "[WRITE ERROR] Usage: write filename.txt content"
        fname, content = parts[1], parts[2]
        path = os.path.join(JEMAI_HUB, fname)
        try:
            with open(path,"w",encoding="utf-8") as f: f.write(content)
            return f"Written to {fname}"
        except Exception as e: return f"[WRITE ERROR] {e}"
    # Basic shell execution
    if lcmd.startswith("run "):
        realcmd = cmd[4:]
        try: out = subprocess.check_output(realcmd, shell=True, stderr=subprocess.STDOUT, timeout=30)
        except Exception as e: return f"[SHELL ERROR] {e}"
        return out.decode(errors="replace")
    # Resource status
    if lcmd in ["status","resources","stats"]:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage(JEMAI_HUB).percent
        return f"CPU: {cpu}%\nRAM: {ram}%\nDisk: {disk}%"
    # Fallback: try shell
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=30)
        return out.decode(errors="replace")
    except Exception as e:
        return f"[UNKNOWN/ERROR] {e}"

# ====================== VERSION CONTROL ============================
def backup_current():
    stamp = datetime.datetime.now().strftime("%d-%m-%Y-%H%M%S")
    dst = os.path.join(VERSIONS_DIR, f"jemai_{stamp}.py")
    try:
        with open(sys.argv[0], "r", encoding="utf-8") as src, open(dst, "w", encoding="utf-8") as out:
            out.write(src.read())
        return dst
    except Exception as e:
        return f"[BACKUP ERROR] {e}"

# ====================== DEVICE INFO/CLUSTER =======================
def device_info():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage(JEMAI_HUB).percent
    host = platform.node()
    osver = platform.platform()
    time = datetime.datetime.now().isoformat()
    access = "Full" if not ACCESS_ERRORS else "ERROR: " + "; ".join(ACCESS_ERRORS)
    files = os.listdir(JEMAI_HUB)
    versions = sorted([f for f in os.listdir(VERSIONS_DIR) if f.endswith(".py")])
    plugins = sorted([f for f in os.listdir(PLUGINS_DIR) if f.endswith(".py")])
    return {
        "host": host,
        "os": osver,
        "cpu": cpu,
        "ram": ram,
        "disk": disk,
        "hub": JEMAI_HUB,
        "access": access,
        "files": files,
        "versions": versions,
        "plugins": plugins,
        "time": time,
    }

# ====================== PLUGIN SYSTEM =============================
PLUGIN_PARSERS = {}
def load_plugins():
    global PLUGIN_PARSERS
    PLUGIN_PARSERS = {}
    for fname in os.listdir(PLUGINS_DIR):
        if fname.endswith(".py"):
            try:
                name = fname[:-3]
                mod_path = os.path.join(PLUGINS_DIR, fname)
                import importlib.util
                spec = importlib.util.spec_from_file_location(name, mod_path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "register"):
                    mod.register(lambda f: PLUGIN_PARSERS.update({name: f}))
            except Exception as e:
                print(f"[PLUGIN ERROR] {fname}: {e}")

# ====================== FLASK WEB SERVER ==========================
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def main_page():
    check_access()
    load_plugins()
    output = ""
    if request.method == "POST":
        cmd = request.form.get("cmd","")
        output = interpret_and_act(cmd)
    dot = "🟢" if not ACCESS_ERRORS else "🔴"
    stats = device_info()
    filelist = "<br>".join(stats["files"])
    versionlist = "<br>".join(stats["versions"])
    pluginlist = "<br>".join(stats["plugins"])
    return render_template_string("""
    <html><head><title>JEMAI AGI OS Shell</title>
    <style>
    body{background:#151b24;color:#e3f8f7;font-family:Segoe UI,Arial,sans-serif;padding:30px;}
    .box{background:#253147;border-radius:17px;padding:38px;max-width:800px;margin:70px auto;}
    .inp{width:95%;font-size:1.16em;padding:13px;margin-bottom:8px;background:#10161e;color:#e7fff5;border-radius:7px;border:none;}
    .btn{font-size:1.13em;padding:10px 30px;background:#40dfc1;color:#183d3b;border:none;border-radius:8px;cursor:pointer;}
    .msg{color:#abff9d;margin:11px 0 4px 0;}
    .err{color:#e47563;}
    pre{background:#222e39;padding:15px 16px;border-radius:7px;margin-top:13px;overflow:auto;}
    </style>
    </head><body>
      <div class="box">
        <div style="font-size:2.1em;font-weight:600;margin-bottom:9px;">JEMAI AGI OS <span style="font-size:0.65em;font-weight:400;color:#7cf5d2;">— Full Power Shell</span>
          <span style="font-size:1.5em;">{{dot}}</span>
        </div>
        <div class="{{'msg' if not ACCESS_ERRORS else 'err'}}">{{stats['access']}}</div>
        <form method="post">
          <input class="inp" name="cmd" autofocus placeholder="Type any command (dir, cat file, write file content, run whoami)..." />
          <button class="btn" type="submit">Run</button>
        </form>
        {% if output %}<pre>{{output}}</pre>{% endif %}
        <div style="margin-top:25px;font-size:1em;color:#79edd7;">
          <b>Hub:</b> {{stats['hub']}}<br>
          <b>Host:</b> {{stats['host']}}<br>
          <b>OS:</b> {{stats['os']}}<br>
          <b>CPU:</b> {{stats['cpu']}}% &nbsp; <b>RAM:</b> {{stats['ram']}}% &nbsp; <b>Disk:</b> {{stats['disk']}}%<br>
          <b>Files:</b> <br><span style="color:#e5fff7;">{{filelist}}</span><br>
          <b>Versions:</b> <br><span style="color:#e3fdb5;">{{versionlist}}</span><br>
          <b>Plugins:</b> <br><span style="color:#e3baff;">{{pluginlist}}</span><br>
          <b>Time:</b> {{stats['time']}}
        </div>
      </div>
    </body></html>
    """, output=output, stats=stats, ACCESS_ERRORS=ACCESS_ERRORS, filelist=filelist, dot=dot,
         versionlist=versionlist, pluginlist=pluginlist)

@app.route("/api/status")
def api_status(): 
    check_access()
    return jsonify(device_info())

@app.route("/api/cmd", methods=["POST"])
def api_cmd():
    check_access()
    cmd = request.json.get("cmd","")
    out = interpret_and_act(cmd)
    return jsonify({"output": out, "access": "Full" if not ACCESS_ERRORS else "ERROR"})

# ====================== CLI SHELL (optional) ======================
def run_cli():
    check_access()
    print("JEMAI AGI OS Shell — Type 'exit' to quit")
    while True:
        cmd = input("JEMAI> ").strip()
        if cmd.lower() in ["exit","quit"]: break
        out = interpret_and_act(cmd)
        print(out.strip() if out else "[No output]")

# ====================== MAIN ENTRY ================================
if __name__ == "__main__":
    threading.Thread(target=run_cli, daemon=True).start()
    app.run("0.0.0.0", 8181, debug=False)
