import os
import json
import time
import threading
import subprocess
import sys
from flask import Flask, request, jsonify, render_template_string
from flask import redirect

# === FLASK SERVER ===
app = Flask(__name__)

@app.route("/")
def root():
    return redirect("/view")


# === CONFIG ===
APP_NAME = "JEMAI"
LOG_FILENAME = "feedback_store.json"
PORT = 9090
HOST = "0.0.0.0"
CHECK_INTERVAL = 0.5
CLIPBOARD_PREFIX = "lt::run"

# === PATH SETUP ===
appdata = os.getenv("APPDATA") or os.path.expanduser("~/.jemai")
app_data_path = os.path.join(appdata, APP_NAME)
os.makedirs(app_data_path, exist_ok=True)
log_file_path = os.path.join(app_data_path, LOG_FILENAME)

# === FLASK SERVER ===
app = Flask(__name__)

HTML_TEMPLATE = '''
<!doctype html>
<html><head><title>JEMAI Tunnel Logs</title></head>
<body style="font-family: monospace; background: #111; color: #0f0; padding: 20px;">
<h2>JEMAI Feedback</h2><hr>
<pre id="logs">{{ logs }}</pre>
<script>
setInterval(() => {
  fetch('/api').then(res => res.json()).then(data => {
    document.getElementById('logs').textContent = JSON.stringify(data, null, 2);
  });
}, 3000);
</script>
</body></html>
'''

@app.route("/upload", methods=["POST"])
def upload():
    try:
        payload = request.get_json(force=True)
        payload["_received"] = time.strftime('%Y-%m-%d %H:%M:%S')
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
        return jsonify({"status": "ok"})
    except Exception as ex:
        return jsonify({"status": "error", "message": str(ex)}), 500

@app.route("/api")
def api():
    if not os.path.isfile(log_file_path): return jsonify([])
    with open(log_file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()[-50:]
    return jsonify([json.loads(l) for l in lines if l.strip()])

@app.route("/view")
def view():
    if not os.path.isfile(log_file_path): return "<b>No logs yet.</b>"
    with open(log_file_path, "r", encoding="utf-8") as f:
        log_text = "\n".join(f.readlines()[-50:])
    return render_template_string(HTML_TEMPLATE, logs=log_text)

# === AGENT CLIPBOARD MONITOR ===
def run_command(command):
    try:
        result = subprocess.run(command, capture_output=True, shell=True, text=True, timeout=30)
        return result.stdout + ("\n" + result.stderr if result.stderr else "")
    except Exception as e:
        return f"[ERROR] {e}"

def clipboard_watcher():
    try:
        import pyperclip, requests
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyperclip", "requests", "flask"])
        import pyperclip, requests
    last = ""
    while True:
        try:
            clip = pyperclip.paste()
            if clip != last and clip.strip().lower().startswith(CLIPBOARD_PREFIX):
                last = clip
                cmd = clip[len(CLIPBOARD_PREFIX):].strip()
                output = run_command(cmd)
                payload = {
                    "agent": "JEMAI_TunnelCore",
                    "command": cmd,
                    "output": output,
                    "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                    "version": "JEMAI_v4.0"
                }
                try:
                    requests.post(f"http://127.0.0.1:{PORT}/upload", json=payload)
                except Exception as post_err:
                    print(f"[POST FAIL] {post_err}")
        except Exception:
            pass
        time.sleep(CHECK_INTERVAL)

# === MAIN ===
def main():
    threading.Thread(target=clipboard_watcher, daemon=True).start()
    app.run(host=HOST, port=PORT, threaded=True)

if __name__ == "__main__":
    main()
