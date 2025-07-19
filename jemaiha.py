import os, sys, subprocess, time, threading, platform, json, psutil, socket, sqlite3, requests, shutil, base64, random, datetime
from flask import Flask, request, jsonify, render_template_string, send_from_directory
try:
    from flask_socketio import SocketIO, emit
except ImportError:
    print("First-time setup: Installing flask_socketio and eventlet...")
    subprocess.run([sys.executable, "-m", "pip", "install", "flask_socketio", "eventlet"], check=True)
    os.execl(sys.executable, sys.executable, *sys.argv)

# ---- AUTO-INSTALL ALL DEPS ON LAUNCH ----
required_packages = [
    "flask", "flask_socketio", "eventlet", "psutil", "chromadb", "requests",
    "edge-tts", "pyttsx3", "python-socketio", "python-engineio"
]
def auto_install(pkgs):
    for pkg in pkgs:
        try:
            __import__(pkg.replace('-', '_').replace('python_', ''))
        except ImportError:
            print(f"[JEMAI] Installing missing: {pkg}")
            subprocess.run([sys.executable, "-m", "pip", "install", pkg, "--user"], check=True)
auto_install(required_packages)

import eventlet; eventlet.monkey_patch()
from flask_socketio import SocketIO, emit

# ---- HOME ASSISTANT INTEGRATION ----
HA_CONF = os.path.expanduser("~/.jemai_ha.json")
def get_ha_conf():
    if os.path.exists(HA_CONF):
        with open(HA_CONF, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_ha_conf(conf):
    with open(HA_CONF, "w", encoding="utf-8") as f:
        json.dump(conf, f, indent=2)

def ha_api(path, method="GET", data=None):
    conf = get_ha_conf()
    if not conf.get("url") or not conf.get("token"):
        return {"error": "HA not configured"}
    url = conf["url"].rstrip("/") + path
    headers = {"Authorization": f"Bearer {conf['token']}", "Content-Type": "application/json"}
    try:
        r = requests.request(method, url, headers=headers, json=data, timeout=7)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def ha_discover_entities(domain="media_player"):
    resp = ha_api(f"/api/states")
    if "error" in resp: return []
    return [x for x in resp if x["entity_id"].startswith(domain)]

def ha_play_media(entity_id, media_url):
    return ha_api(f"/api/services/media_player/play_media", "POST",
                  {"entity_id": entity_id, "media_content_id": media_url, "media_content_type": "music"})

def ha_speak(entity_id, text):
    return ha_api(f"/api/services/tts/google_translate_say", "POST",
                  {"entity_id": entity_id, "message": text})

# ---- CORE SYSTEM/GUI/CHAT ----
HOME = os.path.expanduser("~")
JEMAI_HUB = os.path.join(HOME, "jemai_hub")
os.makedirs(JEMAI_HUB, exist_ok=True)
VERSIONS_DIR = os.path.join(HOME, ".jemai_versions")
os.makedirs(VERSIONS_DIR, exist_ok=True)
SQLITE_PATH = os.path.join(JEMAI_HUB, "jemai_hub.sqlite3")

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# ...[Insert all your chat, RAG, VSCode iframe, drag-drop, file explorer, plugins, model selection, etc here]...

@app.route("/ha", methods=["GET", "POST"])
def homeassistant_ui():
    conf = get_ha_conf()
    msg = ""
    if request.method == "POST":
        url = request.form.get("url")
        token = request.form.get("token")
        if url and token:
            save_ha_conf({"url": url, "token": token})
            msg = "Saved! Try reloading entities."
    entities = ha_discover_entities()
    speakers = [e for e in entities if "sonos" in e["entity_id"] or "media_player" in e["entity_id"]]
    return render_template_string("""
    <h2>Home Assistant Setup</h2>
    <form method=post>
      HA URL: <input name=url value="{{conf.get('url','')}}" size=45><br>
      HA Token: <input name=token value="{{conf.get('token','')}}" size=45><br>
      <button type=submit>Save</button>
      <span style='color:lime;'>{{msg}}</span>
    </form>
    <h3>Speakers / Media Players:</h3>
    <ul>
    {% for s in speakers %}
      <li>{{s.entity_id}} <button onclick="fetch('/ha_speak?eid={{s.entity_id}}&text=Hello+from+JEMAI').then(()=>alert('TTS sent!'));">TTS Test</button>
          <button onclick="fetch('/ha_play?eid={{s.entity_id}}&url=https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3').then(()=>alert('Music sent!'));">Play Test Music</button>
      </li>
    {% endfor %}
    </ul>
    <script>
    function reload() { location.reload(); }
    </script>
    """, conf=conf, msg=msg, speakers=speakers)

@app.route("/ha_speak")
def ha_speak_api():
    eid = request.args.get("eid")
    text = request.args.get("text","Hello from JEMAI")
    out = ha_speak(eid, text)
    return jsonify(out)

@app.route("/ha_play")
def ha_play_api():
    eid = request.args.get("eid")
    url = request.args.get("url")
    out = ha_play_media(eid, url)
    return jsonify(out)

# All other features: [Insert all AGI, group chat, plugin mgmt, RAG etc here as before...]

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8181)
