import os, platform, psutil, datetime
from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)

def get_system_info():
    return {
        "hostname": platform.node(),
        "os": platform.platform(),
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage("/").percent,
        "time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "cwd": os.getcwd(),
    }

def list_dir(path):
    try:
        files = []
        for name in os.listdir(path):
            fpath = os.path.join(path, name)
            files.append({
                "name": name,
                "is_dir": os.path.isdir(fpath),
                "size": os.path.getsize(fpath) if os.path.isfile(fpath) else "-",
                "mtime": datetime.datetime.fromtimestamp(os.path.getmtime(fpath)).strftime('%Y-%m-%d %H:%M:%S'),
            })
        return files
    except Exception as e:
        return [{"name": "ERROR: "+str(e), "is_dir": False, "size": "-", "mtime": "-"}]

@app.route("/")
def index():
    return render_template_string("""
    <html><head>
    <title>Live JEMAI Explorer</title>
    <style>
        body { background:#23263a; color:#e5ffe6; font-family:sans-serif; }
        .sys { background:#2d3250; margin:20px auto 5px auto; border-radius:10px; padding:17px 23px; width:fit-content; }
        .dir { background:#222; margin:10px auto; border-radius:8px; width:88vw; padding:24px; }
        .entry { padding:5px 12px; border-radius:6px; margin:4px; display:inline-block; background:#363f60;}
        .entry.dir { background:#2feec7; color:#20292a; font-weight:600; cursor:pointer; }
    </style>
    <script>
        function reloadDir(path="") {
            fetch('/api/ls?path='+encodeURIComponent(path)).then(r=>r.json()).then(d=>{
                let div = document.getElementById('dir');
                div.innerHTML = "";
                d.files.forEach(f=>{
                    let el = document.createElement('span');
                    el.className = "entry"+(f.is_dir ? " dir" : "");
                    el.innerText = f.name+(f.is_dir?" /":"") + " ("+f.size+")";
                    el.title = "Modified: "+f.mtime;
                    if(f.is_dir) el.onclick = ()=>reloadDir(f.name===".." ? f.name : (d.path==""?f.name:d.path+"/"+f.name));
                    div.appendChild(el);
                });
            });
        }
        function reloadSys() {
            fetch('/api/sys').then(r=>r.json()).then(d=>{
                let sys = document.getElementById('sysinfo');
                sys.innerHTML = `<b>Host:</b> ${d.hostname} | <b>OS:</b> ${d.os} | <b>CPU:</b> ${d.cpu}% | <b>RAM:</b> ${d.ram}% | <b>Disk:</b> ${d.disk}%<br><b>Time:</b> ${d.time} | <b>Dir:</b> ${d.cwd}`;
            });
        }
        setInterval(reloadSys, 2000);
        window.onload = ()=>{ reloadSys(); reloadDir(""); }
    </script>
    </head><body>
        <div class="sys" id="sysinfo"></div>
        <div class="dir" id="dir"></div>
    </body></html>
    """)

@app.route("/api/sys")
def api_sys():
    return jsonify(get_system_info())

@app.route("/api/ls")
def api_ls():
    path = request.args.get("path", "")
    base = os.getcwd()
    dir_path = os.path.abspath(os.path.join(base, path))
    # For security: disallow browsing outside cwd
    if not dir_path.startswith(base):
        return jsonify({"files":[{"name":"[DENIED]", "is_dir":False, "size":"-","mtime":"-"}], "path":path})
    # Add parent dir option
    files = [{"name":"..", "is_dir":True, "size":"-","mtime":"-"}] if path else []
    files += list_dir(dir_path)
    return jsonify({"files":files, "path":path})

if __name__ == "__main__":
    print("Serving explorer on http://localhost:8484")
    app.run("0.0.0.0", 8484, debug=False)
