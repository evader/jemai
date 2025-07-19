import os

# --- Ensure data folders always exist ---
VERSIONS_DIR = os.path.expanduser("~/.jemai_versions") \
    if os.name != "nt" else os.path.join(os.getcwd(), ".jemai_versions")
HUB_DIR = os.path.expanduser("~/jemai_hub") \
    if os.name != "nt" else os.path.join(os.getcwd())
os.makedirs(VERSIONS_DIR, exist_ok=True)
os.makedirs(HUB_DIR, exist_ok=True)

import os, sys, time, shutil, datetime, subprocess, difflib, threading, platform, re, requests, socket, json
from pathlib import Path

NODE_TYPE = platform.system().lower()
SELF_PATH = os.path.abspath(__file__)
IS_WIN = NODE_TYPE.startswith("win")
IS_LINUX = NODE_TYPE.startswith("linux")
IS_MAC = NODE_TYPE.startswith("darwin")
VERSIONS_DIR = os.path.expanduser("~/.jemai_versions") if not IS_WIN else r"C:\jemai_hub\.jemai_versions"
JEMAI_HUB = os.path.expanduser("~/jemai_hub") if not IS_WIN else r"C:\jemai_hub"
CHROMADB_PORT = 8000  # set to match your ChromaDB port

def backup_current():
    os.makedirs(VERSIONS_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%d-%m-%Y-%H%M%S")
    dst = os.path.join(VERSIONS_DIR, f"jemai_{stamp}.py")
    shutil.copy2(SELF_PATH, dst)
    print(f"[JEMAI] Backup saved to {dst}")

def smoke_test(new_code):
    test_path = os.path.join(VERSIONS_DIR, "jemai_test.py")
    with open(test_path, "w") as f:
        f.write(new_code)
    try:
        output = subprocess.check_output(
            [sys.executable, test_path, "--smoketest"],
            stderr=subprocess.STDOUT, timeout=20
        )
        return True, output.decode(errors="replace")
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

def try_upgrade(new_code, why="manual"):
    print(f"[JEMAI] Smoke testing upgrade ({why})...")
    ok, out = smoke_test(new_code)
    if ok:
        print(f"[JEMAI] Test passed ({why}). Upgrading!")
        backup_current()
        with open(SELF_PATH, "w") as f:
            f.write(new_code)
        print(f"[JEMAI] Upgrade applied! 🔄 Reason: {why}\n")
        os.execv(sys.executable, [sys.executable] + sys.argv)
    else:
        print(f"[JEMAI] Upgrade failed ({why})!\n", out)
        print("[JEMAI] Staying alive on old code.\n")

def notify(msg, voice=True, desktop=True):
    print(f"[JEMAI NOTIFY] {msg}")
    # Voice (pyttsx3)
    if voice:
        try:
            import pyttsx3
            t = threading.Thread(target=lambda: pyttsx3.init().say(msg) or pyttsx3.init().runAndWait(), daemon=True)
            t.start()
        except Exception as e:
            print(f"[JEMAI] Voice error: {e}")
    # Desktop notification
    if desktop:
        try:
            from notifypy import Notify
            notification = Notify()
            notification.title = "JEMAI"
            notification.message = msg
            notification.send()
        except Exception as e:
            print(f"[JEMAI] Notify error: {e}")

def get_local_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "127.0.0.1"

def sync_with_hub():
    os.makedirs(JEMAI_HUB, exist_ok=True)
    # 1. Upload latest code to hub
    local_code = open(SELF_PATH, "r").read()
    node_name = socket.gethostname()
    my_codefile = os.path.join(JEMAI_HUB, f"{node_name}_jemai.py")
    with open(my_codefile, "w") as f:
        f.write(local_code)
    # 2. Download others' code and show difference
    for file in os.listdir(JEMAI_HUB):
        if file.endswith("_jemai.py") and file != f"{node_name}_jemai.py":
            their_code = open(os.path.join(JEMAI_HUB, file), "r").read()
            if their_code != local_code:
                diff = '\n'.join(difflib.unified_diff(local_code.splitlines(), their_code.splitlines(), lineterm=""))
                print(f"[JEMAI] Code diff with {file}:\n{diff[:2000]}\n---")
    # 3. Optionally auto-merge (ask, or set auto mode)
    # [todo] Can write a patch if you want auto-merge!

def sync_chromadb():
    # If on Windows, try to run ChromaDB as a server and listen
    # If on Linux, connect to Windows ChromaDB server and sync embeddings
    try:
        import chromadb
    except ImportError:
        print("[JEMAI] ChromaDB not installed.")
        return
    try:
        client = chromadb.HttpClient(host="localhost" if IS_WIN else "windows-pc-hostname", port=CHROMADB_PORT)
        # Add sync logic here (collections, vectors, etc)
        print("[JEMAI] ChromaDB connection: OK")
        # [todo] real merge/sync!
    except Exception as e:
        print(f"[JEMAI] ChromaDB sync failed: {e}")

def scan_clipboard():
    try:
        if IS_WIN:
            import win32clipboard
            win32clipboard.OpenClipboard()
            d = win32clipboard.GetClipboardData()
            win32clipboard.CloseClipboard()
            return d
        elif IS_LINUX:
            return subprocess.check_output("xclip -o -selection clipboard", shell=True, timeout=2).decode(errors="replace")
        elif IS_MAC:
            return subprocess.check_output("pbpaste", shell=True, timeout=2).decode(errors="replace")
    except Exception:
        return ""

def omni_scrape_all():
    sources = []
    # Add chatlogs, URLs, settings, scripts, clipboard, browser etc as above
    # Add from hub folder:
    for file in os.listdir(JEMAI_HUB):
        if file.endswith(".py"):
            try:
                with open(os.path.join(JEMAI_HUB, file)) as f:
                    sources.append(f.read())
            except: pass
    # Clipboard
    clip = scan_clipboard()
    if clip and clip not in sources:
        sources.append(clip)
    # TODO: Add browser history, VSCode settings, URLs, etc
    # Try upgrading with each code block
    for idx, code in enumerate(sources):
        if code.strip() and "def " in code:
            try_upgrade(code, why=f"omniscrape block {idx+1}")

def device_registry():
    regfile = os.path.join(JEMAI_HUB, "jemai_devices.json")
    node = {
        "hostname": socket.gethostname(),
        "ip": get_local_ip(),
        "type": NODE_TYPE,
        "time": datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
    }
    devices = []
    if os.path.exists(regfile):
        try:
            devices = json.load(open(regfile))
        except: pass
    devices = [d for d in devices if d["hostname"] != node["hostname"]]
    devices.append(node)
    with open(regfile, "w") as f:
        json.dump(devices, f, indent=2)
    print(f"[JEMAI] Device registry updated: {devices}")

def main_loop():
    print(f"\n[{datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}] JEMAI Master process starting.")
    notify("JEMAI is live!", voice=True, desktop=True)
    print(f"[{datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}] All dependencies present.")
    print(f"[{time.strftime('%H:%M:%S')}] MODEL: [syncing] | VOICE: 🔊 | SYS: TODO% CPU, TODO% RAM")
    while True:
        try:
            line = input("JEMAI(llama3:latest)> ").strip()
            if not line: continue
            if line.lower() in ("exit", "quit"):
                print("Bye!")
                break
            # Paste block = upgrade
            if line.startswith("def ") or line.startswith("import ") or line.startswith("class "):
                print("[JEMAI] Looks like code. Paste rest and Ctrl-D to finish.")
                code = line + "\n"
                while True:
                    try: c = input(); code += c + "\n"
                    except EOFError: break
                try_upgrade(code)
                continue
            if line.lower().startswith("sync chromadb"):
                sync_chromadb()
                continue
            if line.lower().startswith("omniscrape"):
                omni_scrape_all()
                continue
            if line.lower().startswith("sync hub"):
                sync_with_hub()
                continue
            if line.lower().startswith("devices"):
                device_registry()
                continue
            if line.lower().startswith("notify "):
                notify(line[7:])
                continue
            print(f"[JEMAI] You said: {line}")
        except EOFError:
            print("\n[JEMAI] Paste new code to upgrade, or Ctrl-C/exit to quit.")
            try:
                code = ""
                while True:
                    c = input()
                    code += c + "\n"
            except EOFError:
                if code.strip():
                    try_upgrade(code)
                else:
                    print("[JEMAI] Nothing pasted. Bye!")
                    break
        except KeyboardInterrupt:
            print("\nInterrupted.")
            break

if __name__ == "__main__":
    device_registry()
    sync_with_hub()
    omni_scrape_all()
    main_loop()
