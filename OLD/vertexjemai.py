print(">>> JEMAI AGENT SHELL ACTIVE — If you see this, you are running the interactive AGI OS shell. <<<")
import os, sys, time, shutil, datetime, subprocess, threading, platform, json, difflib, glob, asyncio
from pathlib import Path

# --- CLUSTER UPDATE IMPORTS ---
# Note: This assumes a 'cluster_update.py' file exists in the same directory.
# from cluster_update import zip_dir, serve_update, announce_update, start_update_listener

# A simple mock for cluster_update to allow the script to run standalone
class MockClusterUpdate:
    def zip_dir(self, *args, **kwargs): print("[MOCK] Zipping directory...")
    def serve_update(self, *args, **kwargs): print("[MOCK] Serving update...")
    def announce_update(self, *args, **kwargs): print("[MOCK] Announcing update...")
    def start_update_listener(self, *args, **kwargs): print("[MOCK] Update listener started.")
    def get_ip(self): return "127.0.0.1"

_mock_cu = MockClusterUpdate()
zip_dir = _mock_cu.zip_dir
serve_update = _mock_cu.serve_update
announce_update = _mock_cu.announce_update
start_update_listener = _mock_cu.start_update_listener
# --- END MOCK ---


# --- GLOBALS ---
SELF_PATH = os.path.abspath(__file__)
HOME = str(Path.home())
VERSIONS_DIR = os.path.join(HOME, ".jemai_versions")
JEMAI_HUB = os.path.join(HOME, "jemai_hub")
CHAT_EXPORT = os.path.join(HOME, "chatgpt_export.txt")
WIN_HUB = "C:\\jemai_hub"
SMOKE_TIMEOUT = 20

# --- Start Cluster Update Listener (runs in background, ready to auto-upgrade) ---
CODE_DIR = os.path.dirname(os.path.abspath(__file__))
start_update_listener(CODE_DIR)

# --- VERSION CONTROL ---
def backup_current():
    os.makedirs(VERSIONS_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%d-%m-%Y-%H%M%S")
    dst = os.path.join(VERSIONS_DIR, f"jemai_{stamp}.py")
    with open(SELF_PATH, "r", encoding="utf-8") as src, open(dst, "w", encoding="utf-8") as out:
        out.write(src.read())
    print(f"[JEMAI] Backup saved to {dst}")

# --- DEP CHECK ---
def ensure_dependencies():
    pkgs = ["requests", "pyttsx3", "psutil"]
    missing = []
    for p in pkgs:
        try:
            __import__(p)
        except ImportError:
            missing.append(p)
    # Add edge-tts for Windows
    if platform.system() == "Windows":
        try:
            import edge_tts
        except ImportError:
            missing.append("edge-tts")
    if missing:
        print(f"[JEMAI] Installing missing dependencies: {', '.join(missing)}")
        if platform.system() == "Windows":
            os.system(f"python -m pip install --user {' '.join(missing)}")
        else:
            os.system(f"python3 -m pip install --user {' '.join(missing)} --break-system-packages")
        print("[JEMAI] Dependencies installed. Please restart the script if you see errors above.")
        sys.exit(0)

ensure_dependencies()
import requests, pyttsx3, psutil

# --- VOICE (ChatGPT-4 style on Windows, fallback elsewhere) ---
def say(text, voice="en-US-JennyNeural"):
    print(f"[VOICE] Speaking: {text[:70]}...")
    try:
        if platform.system() == "Windows":
            import edge_tts
            async def speak():
                communicate = edge_tts.Communicate(str(text), voice)
                await communicate.save("edge_tts_output.mp3")
                # Using start /min to avoid a disruptive command window
                os.system('start /min wmplayer "edge_tts_output.mp3"')
            asyncio.run(speak())
        else:
            engine = pyttsx3.init()
            engine.say(str(text))
            engine.runAndWait()
    except Exception as e:
        print(f"[VOICE ERROR] {e}")

# --- OLLAMA SUPPORT ---
def ollama_list_models():
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        if r.ok:
            return [m['name'] for m in r.json().get('models', [])]
        return []
    except requests.exceptions.ConnectionError:
        return ["[OLLAMA ERROR] Connection failed. Is Ollama running?"]
    except Exception as e:
        return [f"[OLLAMA ERROR] {e}"]

def ollama_chat(model, prompt):
    try:
        data = {"model": model, "prompt": prompt, "stream": False}
        r = requests.post("http://localhost:11434/api/generate", json=data, timeout=120)
        if r.ok:
            return r.json().get("response", "").strip()
        return f"[OLLAMA ERR] {r.status_code}: {r.text}"
    except Exception as e:
        return f"[OLLAMA ERR] {e}"

# --- SELF-UPGRADE ---
def smoke_test(new_code):
    os.makedirs(VERSIONS_DIR, exist_ok=True)
    test_path = os.path.join(VERSIONS_DIR, "jemai_test.py")
    with open(test_path, "w", encoding="utf-8") as f:
        f.write(new_code)
    try:
        output = subprocess.check_output(
            [sys.executable, test_path, "--smoketest"],
            stderr=subprocess.STDOUT, timeout=SMOKE_TIMEOUT
        )
        return True, output.decode(errors="replace")
    except Exception as e:
        error_output = e.output.decode(errors="replace") if hasattr(e, 'output') else str(e)
        return False, f"{type(e).__name__}: {error_output}"

def try_upgrade(new_code, why="manual"):
    print(f"[JEMAI] Smoke testing upgrade ({why})...")
    ok, out = smoke_test(new_code)
    if ok:
        print(f"[JEMAI] Test passed. Upgrading!")
        backup_current()
        with open(SELF_PATH, "w", encoding="utf-8") as f:
            f.write(new_code)
        print(f"[JEMAI] Upgrade applied! 🔄 Reason: {why}\nRestarting...")
        os.execv(sys.executable, [sys.executable] + sys.argv)
    else:
        print(f"[JEMAI] Upgrade failed ({why})!\n{out}")
        print("[JEMAI] Staying alive on old code.\n")

# --- OMNI-SCRAPE: APPLY ALL UPGRADE BLOCKS FROM EXPORT/HUB ---
def omniscrape_blocks():
    blocks = []
    # Grab from chat export
    if os.path.exists(CHAT_EXPORT):
        with open(CHAT_EXPORT, encoding="utf-8") as f:
            raw = f.read()
            # Simple block detection
            for chunk in raw.split("\n\n"):
                if chunk.strip().startswith(("import ", "def ", "class ")):
                    blocks.append(chunk.strip())
    # Also scan jemai_hub for other device code
    for hub_path in [JEMAI_HUB, WIN_HUB]:
        if os.path.exists(hub_path):
            for py in glob.glob(os.path.join(hub_path, "jemai*.py")):
                with open(py, encoding="utf-8") as f:
                    code = f.read().strip()
                    if code and code not in blocks:
                        blocks.append(code)
    return blocks

def omni_scrape_all():
    print("[JEMAI] Starting omniscrape to find potential upgrades...")
    blocks = omniscrape_blocks()
    if not blocks:
        print("[JEMAI] Omniscrape found no code blocks to test.")
        return

    current_code = open(SELF_PATH, 'r', encoding='utf-8').read()
    applied_count = 0

    for idx, code_block in enumerate(blocks):
        # A simple diff to see if the new code is meaningfully different
        diff = list(difflib.unified_diff(current_code.splitlines(True), code_block.splitlines(True)))
        if len(diff) < 3: # Not different enough to warrant an upgrade
            continue

        print(f"[JEMAI] Testing omniscrape block {idx+1}/{len(blocks)}...")
        ok, out = smoke_test(code_block)
        if ok:
            print(f"[JEMAI] Test passed for omniscrape block {idx+1}. Applying upgrade.")
            try_upgrade(code_block, why=f"omniscrape block {idx+1}")
            # try_upgrade will restart, so this loop breaks
        else:
            print(f"[JEMAI] Test failed for omniscrape block {idx+1}: {out}")

    print(f"[JEMAI] Omniscrape finished. Checked {len(blocks)} blocks.")

# --- DEVICE REGISTRY ---
def device_registry():
    os.makedirs(JEMAI_HUB, exist_ok=True)
    regfile = os.path.join(JEMAI_HUB, "jemai_devices.json")
    host = platform.node()
    now = datetime.datetime.now().isoformat()
    entry = {'hostname': host, 'os': platform.system(), 'last_seen': now}

    devices = {}
    if os.path.exists(regfile):
        try:
            with open(regfile, 'r', encoding="utf-8") as f:
                devices = json.load(f)
        except json.JSONDecodeError:
            devices = {}
    
    devices[host] = entry
    with open(regfile, "w", encoding="utf-8") as f:
        json.dump(devices, f, indent=2)
    print(f"[JEMAI] Device '{host}' registered/updated in the hub.")

# --- HEALTH & STATUS ---
def status_line(model):
    cpu = f"CPU: {psutil.cpu_percent()}%"
    ram = f"RAM: {psutil.virtual_memory().percent}%"
    
    models = ollama_list_models()
    model_status = f"Ollama Models: {len(models)}" if models else "Ollama: down"
    
    files = sorted(glob.glob(os.path.join(VERSIONS_DIR, '*.py'))) if os.path.exists(VERSIONS_DIR) else []
    versions_str = f"Backups: {len(files)}"
    
    return f"[{datetime.datetime.now().strftime('%H:%M:%S')}] | Model: {model} | {model_status} | {cpu}, {ram} | {versions_str}"

# --- MAIN CLI LOOP ---
def main_loop():
    print(f"\n[{'-'*60}]\n[JEMAI] Master process starting.")
    device_registry()
    omni_scrape_all() # Try upgrades from export/hub first!

    print("[JEMAI NOTIFY] JEMAI is live! All dependencies present.")
    model = "llama3:latest"
    print(status_line(model))

    while True:
        try:
            line = input(f"JEMAI({model})> ").strip()
            if not line:
                continue

            if line.startswith(("import ", "def ", "class ", "from ")):
                print("[JEMAI] Paste-to-upgrade mode. End with Ctrl-D (Unix) or Ctrl-Z+Enter (Win).")
                code_lines = [line]
                while True:
                    try:
                        code_lines.append(input())
                    except EOFError:
                        break
                try_upgrade("\n".join(code_lines), why="manual paste")
                continue

            if line.lower().startswith("model:"):
                model = line.split(":", 1)[1].strip()
                print(f"[JEMAI] Model switched to '{model}'.")
                print(status_line(model))
                continue

            if line.strip().lower() in ['status', 'st']:
                print(status_line(model))
                continue

            if line.split()[0] in ['ls','cd','cat','pwd','ps','top','du','df','find','grep','head','tail']:
                try:
                    # Note: 'cd' is not effective this way as it runs in a subshell.
                    result = subprocess.check_output(line, shell=True, stderr=subprocess.STDOUT, timeout=20, text=True)
                    print(result)
                except Exception as e:
                    print(f"[CMD ERR] {type(e).__name__}: {e}")
                continue

            if line.strip().lower() in ("update", "upgrade", "syncupdate"):
                # from cluster_update import get_ip as cluster_get_ip
                # ip = cluster_get_ip()
                # zip_dir(CODE_DIR, "update.zip")
                # serve_update("update.zip")
                # announce_update(ip)
                print("[JEMAI] Cluster-wide update initiated.")
                continue

            if line.lower().startswith("say "):
                say(line.split("say ", 1)[1])
                continue

            print(f"[{model}]> ", end="", flush=True)
            response = ollama_chat(model, line)
            print(response)
            if response and not response.startswith('[OLLAMA ERR]'):
                say(response)

        except KeyboardInterrupt:
            print("\n[JEMAI] User requested exit. Bye!")
            break
        except Exception as e:
            print(f"[JEMAI] Fatal error in main loop: {e}")
            break

if __name__ == "__main__":
    if "--smoketest" in sys.argv:
        print("[JEMAI] Smoke test OK.")
        sys.exit(0)
    main_loop()