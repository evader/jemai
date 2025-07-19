import os, sys, datetime, difflib, subprocess, threading, shutil
from flask import Flask, request, render_template_string, jsonify, send_from_directory

# === CONFIG ===
JEMAI_VERSIONS = os.environ.get("JEMAI_VERSIONS", r"C:\JEMAI_HUB\OLD\Versions")  # or "~/jemai_hub/OLD/Versions"
JEMAI_CURRENT = os.environ.get("JEMAI_CURRENT", r"C:\JEMAI_HUB\jemai.py")
JEMAI_WIKI_MD = os.path.join(JEMAI_VERSIONS, "JEMAI_WIKI.md")

# Ensure directory exists
os.makedirs(JEMAI_VERSIONS, exist_ok=True)

app = Flask(__name__)
PORT = 18800

# ====== UTILITIES ======
def list_versions():
    files = []
    for fn in sorted(os.listdir(JEMAI_VERSIONS)):
        if fn.endswith(".py") and "-" in fn:
            files.append(fn)
    return files

def readfile(fn):
    with open(os.path.join(JEMAI_VERSIONS, fn), encoding="utf-8", errors="ignore") as f:
        return f.read()

def highlight(code):
    # Cheap syntax highlighting
    import html
    return "<pre style='font-size:1.01em;background:#222;color:#f9f9c9;padding:12px;border-radius:9px;overflow:auto;'>%s</pre>" % html.escape(code)

def diff(a, b):
    a_lines = a.splitlines()
    b_lines = b.splitlines()
    d = difflib.HtmlDiff().make_table(a_lines, b_lines, fromdesc="Old", todesc="New", context=True, numlines=4)
    return d

def save_wiki(md):
    with open(JEMAI_WIKI_MD, "w", encoding="utf-8") as f:
        f.write(md)

def load_wiki():
    if not os.path.exists(JEMAI_WIKI_MD):
        return "# JEMAI WIKI\n\nChangelog and notes here."
    return open(JEMAI_WIKI_MD, encoding="utf-8").read()

def preview_server(fn, port=18801):
    def _run():
        try:
            subprocess.run([sys.executable, os.path.join(JEMAI_VERSIONS, fn)], env={**os.environ, "FLASK_RUN_PORT":str(port)}, timeout=600)
        except Exception as e:
            print(f"Preview crashed: {e}")
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return f"Preview launched on port {port}."

def rollback_version(fn):
    shutil.copy2(os.path.join(JEMAI_VERSIONS, fn), JEMAI_CURRENT)
    return f"Rolled back to {fn}"

# ====== ROUTES ======
@app.route("/")
def wiki_home():
    vers = list_versions()
    md = load_wiki()
    return render_template_string("""
    <html>
    <head>
      <title>JEMAI Wiki, Changelog, Version Browser</title>
      <style>
        body { background: #191d28; color: #ffd; font-family: Segoe UI,Arial; margin:0; padding:0; }
        .main { max-width:1220px; margin:20px auto; background:#262d36; border-radius:16px; padding:25px 30px; }
        h1,h2 { color:#ffd06d; }
        .verslist { font-size:1.11em; margin:12px 0;}
        .versitem { margin:5px 0; padding:4px 7px 4px 0;}
        .versitem a { color:#f8b853; font-weight:600;}
        .btn { padding:3px 12px; border-radius:7px; background:#ffb759; color:#191d28; border:none; cursor:pointer; font-weight:600;}
        .diffpre { background:#222; color:#e7ffb2; font-size:.98em; padding:6px; border-radius:6px;}
        textarea { width:98%; height:290px; margin:7px 0; background:#262d36; color:#ffd; font-family:monospace;}
      </style>
      <script>
      function loadver(fn) {
        fetch('/view?fn='+encodeURIComponent(fn)).then(r=>r.json()).then(j=>{
          document.getElementById('preview').innerHTML = j.code;
        });
      }
      function showdiff(a,b) {
        fetch('/diff?old='+encodeURIComponent(a)+'&new='+encodeURIComponent(b)).then(r=>r.json()).then(j=>{
          document.getElementById('preview').innerHTML = j.diff;
        });
      }
      function previewver(fn) {
        fetch('/preview?fn='+encodeURIComponent(fn)).then(r=>r.json()).then(j=>alert(j.msg));
      }
      function rollback(fn) {
        if(confirm('Rollback to '+fn+'? This will overwrite jemai.py!')) {
          fetch('/rollback?fn='+encodeURIComponent(fn)).then(r=>r.json()).then(j=>alert(j.msg));
        }
      }
      function savewiki() {
        let md = document.getElementById('wikiedit').value;
        fetch('/savewiki', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({md})})
        .then(r=>r.json()).then(j=>alert(j.msg));
      }
      </script>
    </head>
    <body>
      <div class="main">
        <h1>JEMAI Wiki / Changelog</h1>
        <b>Wiki/Changelog (markdown, shared for all users):</b>
        <br>
        <textarea id="wikiedit">{{md}}</textarea><br>
        <button class="btn" onclick="savewiki()">Save Changelog</button>
        <hr>
        <h2>Version History</h2>
        <div class="verslist">
        {% for v in vers %}
          <div class="versitem">
            <a href="javascript:loadver('{{v}}')">{{v}}</a>
            <button class="btn" onclick="showdiff('{{vers[0]}}','{{v}}')">Diff from first</button>
            <button class="btn" onclick="showdiff('{{v}}','{{vers[-1]}}')">Diff to latest</button>
            <button class="btn" onclick="previewver('{{v}}')">Preview</button>
            <button class="btn" onclick="rollback('{{v}}')">Rollback</button>
          </div>
        {% endfor %}
        </div>
        <div id="preview" style="margin:21px 0;"></div>
        <hr>
        <i>All versions in {{JEMAI_VERSIONS}}. Rollback = overwrite jemai.py.</i>
      </div>
    </body>
    </html>
    """, vers=vers, md=md, JEMAI_VERSIONS=JEMAI_VERSIONS)

@app.route("/view")
def api_view():
    fn = request.args.get("fn")
    code = highlight(readfile(fn))
    return jsonify({"code": code})

@app.route("/diff")
def api_diff():
    old = request.args.get("old")
    new = request.args.get("new")
    diff_html = diff(readfile(old), readfile(new))
    return jsonify({"diff": diff_html})

@app.route("/preview")
def api_preview():
    fn = request.args.get("fn")
    msg = preview_server(fn)
    return jsonify({"msg": msg})

@app.route("/rollback")
def api_rollback():
    fn = request.args.get("fn")
    msg = rollback_version(fn)
    return jsonify({"msg": msg})

@app.route("/savewiki", methods=["POST"])
def api_savewiki():
    data = request.json
    save_wiki(data.get("md",""))
    return jsonify({"msg":"Changelog saved!"})

@app.route("/wiki_md")
def serve_md(): return send_from_directory(JEMAI_VERSIONS, "JEMAI_WIKI.md")

if __name__=="__main__":
    app.run("0.0.0.0", PORT, debug=True)
