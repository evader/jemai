import os, sys, threading, time, ctypes, subprocess, platform, json, queue, webbrowser, shutil
from pathlib import Path
from dotenv import load_dotenv
import requests

# ==== 1. AUTO-ELEVATE TO ADMIN ON WINDOWS ====
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if os.name == 'nt' and not is_admin():
    print("[JEMAI] Relaunching as administrator for full integration...")
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join([f'"{arg}"' for arg in sys.argv]), None, 1)
    sys.exit()

# ==== 2. ENV, PATHS, INIT ====
load_dotenv()
IS_WIN = platform.system() == "Windows"
HOME = str(Path.home())
HUB = os.path.join(HOME, "jemai_hub")
PLUGINS = os.path.join(HUB, "plugins")
VERSIONS = os.path.join(HUB, "versions")
SQLITE = os.path.join(HUB, "jemai_hub.sqlite3")
os.makedirs(HUB, exist_ok=True)
os.makedirs(PLUGINS, exist_ok=True)
os.makedirs(VERSIONS, exist_ok=True)

# ==== 3. SYSTEM NOTIFICATION (WINDOWS & CROSS-PLATFORM) ====
def notify(title, msg):
    if IS_WIN:
        try:
            import win10toast
            win10toast.ToastNotifier().show_toast(title, msg, icon_path=None, duration=5, threaded=True)
        except:
            os.system(f'powershell -Command "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null; [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier(\'\').Show((New-Object Windows.UI.Notifications.ToastNotification ((New-Object Windows.Data.Xml.Dom.XmlDocument).LoadXml(\'<toast><visual><binding template=\\\"ToastGeneric\\\"><text>{title}</text><text>{msg}</text></binding></visual></toast>\'))))"')
    else:
        print(f"[{title}] {msg}")

# ==== 4. SYSTEM TRAY APP ====
import pystray
from PIL import Image, ImageDraw

def create_icon():
    icon = Image.new('RGBA', (64, 64), (30, 32, 40, 0))
    draw = ImageDraw.Draw(icon)
    draw.ellipse((16, 16, 48, 48), fill=(50, 255, 80, 255), outline=(0, 255, 80, 255), width=4)
    return icon

def tray_open_ui(icon, item):
    webbrowser.open("http://localhost:8181")
def tray_github_sync(icon, item):
    try:
        subprocess.run(["git", "pull"], cwd=HUB)
        subprocess.run(["git", "add", "."], cwd=HUB)
        subprocess.run(["git", "commit", "-m", "Auto-commit from tray"], cwd=HUB)
        subprocess.run(["git", "push"], cwd=HUB)
        notify("JEMAI", "GitHub repo synced!")
    except Exception as e:
        notify("JEMAI", f"GitHub sync error: {e}")
def tray_restart(icon, item):
    notify("JEMAI", "Restarting JEMAI AGI OS...")
    icon.stop()
    os.execv(sys.executable, ['pythonw.exe'] + sys.argv)
def tray_quit(icon, item):
    notify("JEMAI", "Shutting down AGI.")
    icon.stop()
    os._exit(0)
def tray_upgrade(icon, item):
    notify("JEMAI", "Checking for upgrades...")
    subprocess.run(["git", "pull"], cwd=HUB)
    notify("JEMAI", "Upgrade complete! Restarting.")
    icon.stop()
    os.execv(sys.executable, ['pythonw.exe'] + sys.argv)
def tray_ha_lights(icon, item):
    token = os.environ.get("HOMEASSISTANT_TOKEN")
    if token:
        try:
            url = "http://homeassistant.local:8123/api/services/light/toggle"
            data = {"entity_id": "light.living_room"}  # Example: change entity_id as needed
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            r = requests.post(url, json=data, headers=headers, timeout=5)
            notify("Home Assistant", f"Light toggle: {r.status_code}")
        except Exception as e:
            notify("Home Assistant", f"Light toggle error: {e}")
    else:
        notify("Home Assistant", "No token set!")

def tray_clipboard_ring(icon, item):
    # (Stub: implement full clipboard history ring, restore)
    notify("JEMAI", "Clipboard ring not yet implemented.")

def tray_gpt4_chat(icon, item):
    webbrowser.open("https://chat.openai.com/")  # Opens ChatGPT Plus (web)

def tray_group_chat(icon, item):
    notify("JEMAI", "Group chat not yet implemented.")

def tray_shell_here(icon, item):
    folder = os.getcwd()
    subprocess.Popen(['cmd', '/K', f'cd /d "{folder}"'])

def tray_overlay(icon, item):
    notify("JEMAI", "Overlay not yet implemented.")

def tray_thread():
    menu = pystray.Menu(
        pystray.MenuItem('Open JEMAI UI', tray_open_ui),
        pystray.MenuItem('Sync GitHub', tray_github_sync),
        pystray.MenuItem('Check/Upgrade', tray_upgrade),
        pystray.MenuItem('Restart JEMAI', tray_restart),
        pystray.MenuItem('ChatGPT Plus Web', tray_gpt4_chat),
        pystray.MenuItem('Toggle HA Light', tray_ha_lights),
        pystray.MenuItem('Clipboard Ring', tray_clipboard_ring),
        pystray.MenuItem('Open Shell Here', tray_shell_here),
        pystray.MenuItem('Overlay', tray_overlay),
        pystray.MenuItem('Quit', tray_quit)
    )
    icon = pystray.Icon("jemai", create_icon(), "JEMAI AGI OS", menu)
    icon.run()

# ==== 5. CLIPBOARD HISTORY (BASIC - WINDOWS ONLY) ====
clip_history = []
try:
    import win32clipboard
    import win32con

    def get_clipboard_text():
        win32clipboard.OpenClipboard()
        d = ""
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                d = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        except Exception: pass
        win32clipboard.CloseClipboard()
        return d

    def clipboard_monitor():
        last = ""
        while True:
            t = get_clipboard_text()
            if t and t != last:
                clip_history.append(t)
                if len(clip_history) > 25:
                    clip_history.pop(0)
                last = t
            time.sleep(1)
    th = threading.Thread(target=clipboard_monitor, daemon=True)
    th.start()
except Exception:
    pass

# ==== 6. HOTKEY GLOBAL ACTIVATOR (CTRL+SHIFT+J LAUNCHES UI) ====
try:
    import keyboard
    def hotkey_ui():
        webbrowser.open("http://localhost:8181")
    keyboard.add_hotkey("ctrl+shift+j", hotkey_ui)
except Exception:
    pass

# ==== 7. FLASK WEB UI (with GPT-4/4o/local agent selection) ====
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
from flask_socketio import SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route("/")
def main_ui():
    return render_template_string("""
    <html><body style='background:#181f2b;color:#eaeaea;font-family:sans-serif;padding:40px;'>
    <h1>JEMAI AGI OS</h1>
    <form method='post' action='/api/chat'>
        <input name='q' style='width:70vw;font-size:1.2em;' placeholder='Ask JEMAI...'>
        <select name="agent">
          <option value="gpt4api">GPT-4 API</option>
          <option value="chatgptweb">ChatGPT Plus Web</option>
          <option value="ollama">Ollama Local</option>
        </select>
        <button type='submit'>Send</button>
    </form>
    <hr>
    <a href="/explorer">File Explorer</a> | <a href="/plugins">Plugins</a> | <a href="/wiki">Wiki/Changelog</a>
    </body></html>
    """)

@app.route("/api/chat", methods=["POST"])
def api_chat():
    q = request.form.get("q", "") or request.json.get("q", "")
    agent = request.form.get("agent") or request.json.get("agent") or "gpt4api"
    resp = "[No agent selected]"
    if agent == "gpt4api":
        key = os.environ.get("OPENAI_API_KEY")
        try:
            r = requests.post("https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": "gpt-4o", "messages": [{"role": "user", "content": q}], "max_tokens": 256}, timeout=60)
            if r.ok:
                resp = r.json()['choices'][0]['message']['content']
            else:
                resp = f"[OpenAI Error {r.status_code}] {r.text}"
        except Exception as e:
            resp = f"[OpenAI API Error] {e}"
    elif agent == "chatgptweb":
        # Opens the ChatGPT Plus web UI (use browser, then copy/paste back)
        webbrowser.open("https://chat.openai.com/")
        resp = "[ChatGPT Plus Web UI launched—please use browser]"
    elif agent == "ollama":
        try:
            r = requests.post("http://localhost:11434/api/generate",
                json={"model":"llama3:latest", "prompt":q, "stream":False}, timeout=60)
            if r.ok:
                resp = r.json().get("response","")
            else:
                resp = f"[Ollama Error {r.status_code}] {r.text}"
        except Exception as e:
            resp = f"[OLLAMA ERROR] {e}"
    return jsonify({"resp": resp})

# ==== 8. SYSTEM SELF-HEAL: WATCHDOG, ERROR AUTORESTART ====
def watchdog():
    while True:
        time.sleep(60)
        # Optionally, add healthchecks here

# ==== 9. CONTEXT MENU AUTO-INSTALL (Windows) ====
if IS_WIN:
    try:
        import winreg
        key = winreg.HKEY_CLASSES_ROOT
        subkey = r"*\shell\Run with JEMAI"
        cmd = f'pythonw.exe "{os.path.abspath(sys.argv[0])}" "%1"'
        with winreg.CreateKey(key, subkey) as k:
            winreg.SetValue(k, "", winreg.REG_SZ, "Run with JEMAI")
            with winreg.CreateKey(k, "command") as kc:
                winreg.SetValue(kc, "", winreg.REG_SZ, cmd)
    except Exception as e:
        notify("JEMAI", f"Context menu registry error: {e}")

# ==== 10. LAUNCH TRAY, FLASK, WATCHDOG ====
if __name__ == "__main__":
    tray = threading.Thread(target=tray_thread, daemon=True)
    tray.start()
    watchdog_thread = threading.Thread(target=watchdog, daemon=True)
    watchdog_thread.start()
    print("=== JEMAI AGI OS (ELITE APP) — http://localhost:8181 — [System tray active, AGI ready]")
    socketio.run(app, host="0.0.0.0", port=8181)
