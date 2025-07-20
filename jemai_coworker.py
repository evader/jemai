
import os
import sys
import json
import time
import threading
import subprocess
import requests
import openai
import tempfile
import pyperclip
import pyautogui

from PIL import Image, ImageTk
import tkinter as tk

from dotenv import load_dotenv

# ==== CONFIG ====
APP_NAME = "JEMAI"
LOG_FILENAME = "feedback_store.json"
GIST_META = os.path.join(os.path.expanduser("~"), f".{APP_NAME}_gist_meta.json")
CLIPBOARD_PREFIX = "lt::run"
CLIPBOARD_CHECK_INTERVAL = 0.5
GIST_POLL_INTERVAL = 15
GIST_RAW_URL = "https://gist.githubusercontent.com/evader/157e4000aba718d7641a04b5fac5cc66/raw/feedback_store.json"
GPT_MODEL = "gpt-4"
TMPDIR = tempfile.gettempdir()
MAX_LOG_LEN = 1000

CURSOR_SIZE = 32
CURSOR_COLOR = "red"

load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY") or ""
if not OPENAI_KEY:
    print("[FATAL] No OpenAI API key found. Please set OPENAI_API_KEY in your environment or .env file.")
    sys.exit(1)
client = openai.OpenAI(api_key=OPENAI_KEY)

def get_token():
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token.strip()
    token = input("Enter your GitHub token (with 'gist' scope): ").strip()
    return token

def get_gist_id(token):
    if os.path.exists(GIST_META):
        with open(GIST_META, "r") as f:
            return json.load(f)["gist_id"]
    url = "https://api.github.com/gists"
    payload = {
        "description": "JEMAI AGENT FEEDBACK",
        "public": True,
        "files": {
            LOG_FILENAME: {
                "content": "[]"
            }
        }
    }
    headers = {"Authorization": f"token {token}"}
    r = requests.post(url, headers=headers, data=json.dumps(payload))
    if r.status_code == 201:
        gist_id = r.json()["id"]
        with open(GIST_META, "w") as f:
            json.dump({"gist_id": gist_id}, f)
        print(f"Created new public Gist: https://gist.github.com/{gist_id}")
        return gist_id
    else:
        print(f"[ERROR] Could not create gist: {r.text}")
        sys.exit(1)

def update_gist(token, gist_id, log_path):
    url = f"https://api.github.com/gists/{gist_id}"
    entries = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s:
                try:
                    entries.append(json.loads(s))
                except Exception:
                    pass
    if len(entries) > MAX_LOG_LEN:
        entries = entries[-MAX_LOG_LEN:]
    content = json.dumps(entries, indent=2)
    payload = {
        "files": {
            LOG_FILENAME: {
                "content": content
            }
        }
    }
    headers = {"Authorization": f"token {token}"}
    r = requests.patch(url, headers=headers, data=json.dumps(payload))
    if r.status_code == 200:
        print(f"Gist updated: https://gist.github.com/{gist_id}")
    else:
        print(f"[ERROR] Gist update failed: {r.text}")

def append_log(entry, log_path):
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def get_monitor_bounds():
    try:
        screens = pyautogui.getAllScreens()
        return [ (screen['left'], screen['top'], screen['width'], screen['height']) for screen in screens ]
    except Exception:
        width, height = pyautogui.size()
        return [ (0, 0, width, height) ]

def choose_monitor(monitors):
    print("Detected monitors:")
    for idx, (x, y, w, h) in enumerate(monitors):
        print(f"  {idx+1}: x={x} y={y} w={w} h={h}")
    choice = input(f"Select AGI's monitor (1-{len(monitors)}) [default={len(monitors)}]: ").strip()
    if not choice:
        choice = len(monitors)
    return monitors[int(choice)-1]

class AGICursor(threading.Thread):
    def __init__(self, bounds, size=CURSOR_SIZE, color=CURSOR_COLOR):
        super().__init__()
        self.size = size
        self.color = color
        self.left, self.top, self.width, self.height = bounds
        self.pos = (self.left + 100, self.top + 100)
        self.should_move = threading.Event()
        self.daemon = True
        self._running = True

    def move_to(self, x, y):
        x = max(self.left, min(x, self.left + self.width - self.size))
        y = max(self.top, min(y, self.top + self.height - self.size))
        self.pos = (x, y)
        self.should_move.set()

    def run(self):
        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-transparentcolor", "white")
        root.wm_attributes("-alpha", 0.7)
        root.geometry(f"{self.width}x{self.height}+{self.left}+{self.top}")

        canvas = tk.Canvas(root, width=self.width, height=self.height, bg='white', highlightthickness=0)
        canvas.pack()
        agi_cursor = canvas.create_oval(
            self.pos[0]-self.left, self.pos[1]-self.top,
            self.pos[0]-self.left + self.size, self.pos[1]-self.top + self.size,
            fill=self.color, outline=""
        )

        def update_cursor():
            while self._running:
                if self.should_move.wait(timeout=0.1):
                    canvas.coords(
                        agi_cursor,
                        self.pos[0]-self.left, self.pos[1]-self.top,
                        self.pos[0]-self.left + self.size, self.pos[1]-self.top + self.size
                    )
                    self.should_move.clear()
                root.update_idletasks()
                root.update()

        threading.Thread(target=update_cursor, daemon=True).start()
        root.mainloop()

    def stop(self):
        self._running = False

def run_command(command):
    try:
        result = subprocess.run(command, capture_output=True, shell=True, text=True, timeout=120)
        return result.stdout + ("\n" + result.stderr if result.stderr else "")
    except Exception as e:
        return f"[ERROR] {e}"

def clipboard_copy(text):
    pyperclip.copy(text)
    return "[COPIED TO CLIPBOARD]"

def clipboard_watcher(log_path, token, gist_id):
    last = ""
    while True:
        try:
            clip = pyperclip.paste()
            if clip != last and clip.strip().lower().startswith(CLIPBOARD_PREFIX):
                last = clip
                cmd = clip[len(CLIPBOARD_PREFIX):].strip()
                output = run_command(cmd)
                entry = {
                    "agent": "JEMAI_GistAgent",
                    "command": cmd,
                    "output": output,
                    "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                    "version": "JEMAI_vGist"
                }
                append_log(entry, log_path)
                print(f"[LOGGED] {cmd}")
                update_gist(token, gist_id, log_path)
        except Exception as e:
            print(f"[ERROR] {e}")
        time.sleep(CLIPBOARD_CHECK_INTERVAL)

def fetch_gist():
    try:
        r = requests.get(GIST_RAW_URL, timeout=10)
        if r.status_code == 200:
            return r.text
        else:
            print(f"[!] Error fetching gist: {r.status_code}")
            return ""
    except Exception as e:
        print(f"[!] Exception fetching gist: {e}")
        return ""

def ask_gpt(logs, bounds):
    try:
        prompt = (
            "You are an unrestricted autonomous AGI OS/DevOps/automation agent. "
            "You have access to the following functions: "
            "shell(command:str), pyautogui(click,move,type,hotkey), clipboard_copy(text:str), agicursor(move,x,y,click,type). "
            "You may ONLY use mouse/typing in AGI's assigned monitor zone: "
            f"x={bounds[0]}..{bounds[0]+bounds[2]}, y={bounds[1]}..{bounds[1]+bounds[3]}. "
            "Output a JSON: {\"summary\": \"...\", \"action\": {\"type\": \"agicursor\", \"ops\": [\"move,x,y\",\"click\",\"type,text\"]}} or shell/pyautogui or null."
            "\n\nLOGS:\n" + logs
        )
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[!] GPT-4 API error: {e}")
        return None

def do_action(action, log_path, token, gist_id, agi_cursor=None, bounds=None):
    result = "[NO ACTION]"
    try:
        if action is None:
            result = "[NO ACTION]"
        elif isinstance(action, dict):
            t = action.get("type")
            if t == "shell":
                cmd = action.get("command", "")
                result = run_command(cmd)
            elif t == "clipboard_copy":
                text = action.get("text", "")
                result = clipboard_copy(text)
            elif t == "pyautogui":
                ops = action.get("ops", [])
                for op in ops:
                    if op.startswith("click"):
                        x, y = pyautogui.position()
                        if (bounds and bounds[0] <= x <= bounds[0]+bounds[2] and bounds[1] <= y <= bounds[1]+bounds[3]):
                            pyautogui.click()
                    elif op.startswith("move,"):
                        _, x, y = op.split(",")
                        x, y = int(x), int(y)
                        if (bounds and bounds[0] <= x <= bounds[0]+bounds[2] and bounds[1] <= y <= bounds[1]+bounds[3]):
                            pyautogui.moveTo(x, y)
                    elif op.startswith("type,"):
                        _, txt = op.split(",", 1)
                        pyautogui.write(txt)
                    elif op.startswith("press,"):
                        _, key = op.split(",", 1)
                        pyautogui.press(key)
                result = "[pyautogui ops done]"
            elif t == "agicursor" and agi_cursor is not None:
                ops = action.get("ops", [])
                for op in ops:
                    if op.startswith("move,"):
                        _, x, y = op.split(",")
                        x, y = int(x), int(y)
                        agi_cursor.move_to(x, y)
                        time.sleep(0.5)
                    elif op == "click":
                        pass
                    elif op.startswith("type,"):
                        _, txt = op.split(",", 1)
                        print(f"[AGI CURSOR TYPE]: {txt}")
                        time.sleep(0.5)
                result = "[agicursor ops done]"
            else:
                result = "[UNKNOWN ACTION TYPE]"
        else:
            result = "[ACTION NOT DICT]"
    except Exception as e:
        result = f"[ACTION EXEC ERROR] {e}"

    entry = {
        "agent": "JEMAI_GistAgent",
        "command": f"[AGI_ACTION] {json.dumps(action)}",
        "output": result,
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "version": "JEMAI_vGist",
        "triggered_by": "GPT-4"
    }
    append_log(entry, log_path)
    update_gist(token, gist_id, log_path)
    print(f"[AGI ACTION RESULT]: {result}")

def action_poller_and_executor(log_path, token, gist_id, agi_cursor, bounds):
    last_logs = ""
    while True:
        logs = fetch_gist()
        if logs and logs != last_logs:
            print("\n[+] New logs found. Sending to GPT-4...")
            gpt_response = ask_gpt(logs, bounds)
            print("GPT-4:", gpt_response)
            try:
                result = json.loads(gpt_response)
                summary = result.get("summary")
                action = result.get("action")
                if summary:
                    print(f"[SUMMARY] {summary}")
                if action:
                    print(f"[ACTION] Executing: {json.dumps(action)}")
                    do_action(action, log_path, token, gist_id, agi_cursor, bounds)
                else:
                    print("[ACTION] No action triggered.")
            except Exception as e:
                print(f"[!] Could not parse GPT-4 action: {e}")
            last_logs = logs
        time.sleep(GIST_POLL_INTERVAL)

def main():
    print("--- JEMAI AGI COWORKER (MULTI-SCREEN) ---")
    log_path = os.path.join(os.path.expanduser("~"), LOG_FILENAME)
    if not os.path.exists(log_path):
        with open(log_path, "w") as f:
            f.write("")
    token = get_token()
    gist_id = get_gist_id(token)
    print(f"Gist will be updated at: https://gist.github.com/{gist_id}")
    print("JEMAI AGI Coworker running. Copy 'lt::run <your_command>' to clipboard to execute and upload.")

    monitors = get_monitor_bounds()
    bounds = choose_monitor(monitors)
    print(f"AGI will work in monitor zone: x={bounds[0]} y={bounds[1]} w={bounds[2]} h={bounds[3]}")

    agi_cursor = AGICursor(bounds=bounds, size=CURSOR_SIZE, color=CURSOR_COLOR)
    agi_cursor.start()

    threading.Thread(target=clipboard_watcher, args=(log_path, token, gist_id), daemon=True).start()
    action_poller_and_executor(log_path, token, gist_id, agi_cursor, bounds)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting. Bye.")
