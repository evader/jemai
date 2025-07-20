import os, sys, time, threading, subprocess, json, re, pyperclip, keyboard, requests, pyttsx3
import win32gui, win32con, win32clipboard
from datetime import datetime

# ==== SETTINGS ====
JEMAI_HUB = "C:\\JEMAI_HUB"
LOG_FILE = os.path.join(JEMAI_HUB, "jemai_chat_monitor.log")
CMD_HISTORY = os.path.join(JEMAI_HUB, "jemai_cmd_history.txt")
HOME_ASSISTANT_URL = "http://homeassistant.local:8123/api/services"
HOME_ASSISTANT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI4ZTgxMjMwMzVjNzA0OTYwYjNhMGJjMjFjNTkwZjlmYiIsImlhdCI6MTc1MjkxMDczNCwiZXhwIjoyMDY4MjcwNzM0fQ.Gx2sVQK5cCi9hUhMSiZc_WmTdm0edDqkFBD7SOfn97E"  # <-- YOUR TOKEN
KEYWORDS = ["turn on", "turn off", "say", "play", "run", "restart", "shutdown", "launch", "open"]
ADMIN_MODE = True  # FULL UNRESTRICTED

def log(msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{now}] {msg}\n")
    print(f"[JEMAI] {msg}")

def speak(txt):
    try:
        engine = pyttsx3.init()
        engine.say(txt)
        engine.runAndWait()
    except Exception as e:
        log(f"[VOICE_ERR] {e}")

def notify(txt):
    speak(txt)
    print(f"[NOTIFY] {txt}")

def execute(cmd):
    log(f"Executing command: {cmd}")
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, encoding="utf-8", timeout=90)
        log(out)
        notify("Command complete.")
        return out
    except Exception as e:
        log(f"[CMD_ERR] {e}")
        notify("Command failed.")
        return str(e)

def control_home_assistant(service, entity_id):
    url = f"{HOME_ASSISTANT_URL}/{service}"
    headers = {
        "Authorization": f"Bearer {HOME_ASSISTANT_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {"entity_id": entity_id}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=7)
        if r.ok:
            log(f"Home Assistant {service} {entity_id}: OK")
            notify(f"{service} {entity_id} OK")
        else:
            log(f"Home Assistant ERR: {r.status_code} {r.text}")
            notify(f"Home Assistant ERR {r.status_code}")
    except Exception as e:
        log(f"[HA_ERR] {e}")
        notify("Home Assistant error.")

def get_foreground_window_text():
    hwnd = win32gui.GetForegroundWindow()
    length = win32gui.SendMessage(hwnd, win32con.WM_GETTEXTLENGTH) + 1
    buf = win32gui.PyMakeBuffer(length)
    win32gui.SendMessage(hwnd, win32con.WM_GETTEXT, length, buf)
    text = buf[:length*2].tobytes().decode(errors="ignore")
    return text

def process_text(txt):
    txt = txt.strip()
    log(f"Processing: {txt[:120]}")
    # Home Assistant
    if "kitchen light" in txt.lower():
        if "off" in txt.lower():
            control_home_assistant("light/turn_off", "light.kitchen")
        elif "on" in txt.lower():
            control_home_assistant("light/turn_on", "light.kitchen")
        return
    # OS Commands
    if any(k in txt.lower() for k in KEYWORDS) and ADMIN_MODE:
        execute(txt)
        return
    # Python code blocks (```python ... ```)
    if "```python" in txt or "```" in txt:
        code = re.findall(r"```(?:python)?(.*?)```", txt, re.DOTALL)
        for c in code:
            fname = os.path.join(JEMAI_HUB, f"auto_script_{int(time.time())}.py")
            with open(fname, "w", encoding="utf-8") as f:
                f.write(c)
            log(f"Saved script: {fname}")
            try:
                output = subprocess.check_output([sys.executable, fname], stderr=subprocess.STDOUT, timeout=30, encoding="utf-8")
                log(f"[SCRIPT OUT] {output}")
                notify("Script executed.")
            except Exception as e:
                log(f"[SCRIPT ERR] {e}")
                notify("Script error.")
        return
    # Shell commands
    if txt.lower().startswith("cmd:") or txt.lower().startswith("powershell:"):
        cmd = txt.split(":",1)[1].strip()
        execute(cmd)
        return
    log("No recognized action.")

def clipboard_watcher():
    last_clip = ""
    while True:
        try:
            current_clip = pyperclip.paste()
            if current_clip != last_clip and current_clip.strip():
                last_clip = current_clip
                process_text(current_clip)
        except Exception as e:
            log(f"[CLIP_ERR] {e}")
        time.sleep(1)

def window_text_watcher():
    last_txt = ""
    while True:
        try:
            txt = get_foreground_window_text()
            if txt != last_txt and txt.strip():
                last_txt = txt
                process_text(txt)
        except Exception as e:
            log(f"[WIN_ERR] {e}")
        time.sleep(1.3)

def keyboard_hotkey():
    keyboard.add_hotkey("ctrl+shift+j", lambda: process_text(pyperclip.paste()))

def main():
    log("=== JEMAI Chat Monitor: Started ===")
    threading.Thread(target=clipboard_watcher, daemon=True).start()
    threading.Thread(target=window_text_watcher, daemon=True).start()
    threading.Thread(target=keyboard_hotkey, daemon=True).start()
    notify("JEMAI Chat Monitor running. Copy or say any command to act.")

if __name__ == "__main__":
    main()
