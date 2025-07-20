
import os
import sys
import json
import time
import threading
import subprocess
import requests
import openai
import re

try:
    import pyperclip
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyperclip"])
    import pyperclip

try:
    from screeninfo import get_monitors
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "screeninfo"])
    from screeninfo import get_monitors

from dotenv import load_dotenv
load_dotenv()

# === CONFIG ===
APP_NAME = "JEMAI"
LOG_FILENAME = "feedback_store.json"
GIST_META = os.path.join(os.path.expanduser("~"), f".{APP_NAME}_gist_meta.json")
CLIPBOARD_PREFIX = "lt::run"
CLIPBOARD_CHECK_INTERVAL = 0.5
GIST_POLL_INTERVAL = 10
GIST_RAW_URL = "https://gist.githubusercontent.com/evader/157e4000aba718d7641a04b5fac5cc66/raw/feedback_store.json"
GPT_MODEL = "gpt-4"
DEBUG = False

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_KEY:
    print("[FATAL] Missing OpenAI API Key")
    sys.exit(1)
client = openai.OpenAI(api_key=OPENAI_KEY)

def get_token():
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token.strip()
    return input("Enter your GitHub token (with 'gist' scope): ").strip()

def get_gist_id(token):
    if os.path.exists(GIST_META):
        with open(GIST_META, "r") as f:
            return json.load(f)["gist_id"]
    url = "https://api.github.com/gists"
    payload = {
        "description": "JEMAI AGENT FEEDBACK",
        "public": True,
        "files": {LOG_FILENAME: {"content": "[]"}}
    }
    headers = {"Authorization": f"token {token}"}
    r = requests.post(url, headers=headers, data=json.dumps(payload))
    if r.status_code == 201:
        gist_id = r.json()["id"]
        with open(GIST_META, "w") as f:
            json.dump({"gist_id": gist_id}, f)
        print(f"Created new Gist: https://gist.github.com/{gist_id}")
        return gist_id
    else:
        print(f"[ERROR] Cannot create gist: {r.text}")
        sys.exit(1)

def update_gist(token, gist_id, log_path):
    entries = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s:
                try:
                    entries.append(json.loads(s))
                except:
                    pass
    content = json.dumps(entries, indent=2)
    payload = {"files": {LOG_FILENAME: {"content": content}}}
    headers = {"Authorization": f"token {token}"}
    r = requests.patch(f"https://api.github.com/gists/{gist_id}", headers=headers, data=json.dumps(payload))
    if r.status_code != 200:
        print(f"[ERROR] Gist update failed: {r.text}")

def run_command(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, shell=True, text=True, timeout=60)
        return result.stdout.strip() + ("
" + result.stderr.strip() if result.stderr else "")
    except Exception as e:
        return f"[ERROR] {str(e)}"

def append_log(entry, log_path):
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def sanitize_gpt_response(resp):
    # Remove triple backticks and parse JSON
    clean = re.sub(r"```(?:json)?", "", resp).strip().strip("`")
    match = re.search(r"{.*}", clean, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None

def clipboard_watcher(log_path, token, gist_id):
    last_clip = ""
    while True:
        try:
            clip = pyperclip.paste()
            if clip != last_clip and clip.strip().lower().startswith(CLIPBOARD_PREFIX):
                last_clip = clip
                cmd = clip[len(CLIPBOARD_PREFIX):].strip()
                output = run_command(cmd)
                entry = {
                    "agent": "JEMAI_Coworker",
                    "command": cmd,
                    "output": output,
                    "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                    "version": "JEMAI_vAuto"
                }
                append_log(entry, log_path)
                update_gist(token, gist_id, log_path)
                print(f"[LOGGED] {cmd}")
        except Exception as e:
            print(f"[ERROR] {e}")
        time.sleep(CLIPBOARD_CHECK_INTERVAL)

def fetch_gist_logs():
    try:
        r = requests.get(GIST_RAW_URL, timeout=10)
        return r.text if r.status_code == 200 else ""
    except:
        return ""

def ask_gpt(logs):
    prompt = (
        "You are a shell automation agent. Analyze the latest JSON log and determine:
"
        "- Summary of last action
"
        "- If a follow-up command is required, respond as JSON: "
        '{"summary": "...", "action": "next_command"} or {"summary": "...", "action": null}.

'
        "LOGS:
" + logs
    )
    try:
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[GPT ERROR] {e}")
        return None

def action_executor(log_path, token, gist_id):
    last = ""
    while True:
        logs = fetch_gist_logs()
        if logs and logs != last:
            print("[+] New logs found. Sending to GPT-4...")
            gpt_output = ask_gpt(logs)
            if DEBUG: print("GPT RAW:", gpt_output)
            result = sanitize_gpt_response(gpt_output)
            if result:
                print("[SUMMARY]", result.get("summary", "No summary"))
                action = result.get("action")
                if action:
                    print("[ACTION] Triggering:", action)
                    out = run_command(action)
                    entry = {
                        "agent": "JEMAI_Coworker",
                        "command": action,
                        "output": out,
                        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                        "version": "JEMAI_vAuto",
                        "triggered_by": "GPT-4"
                    }
                    append_log(entry, log_path)
                    update_gist(token, gist_id, log_path)
            else:
                print("[!] GPT-4 response could not be parsed.")
            last = logs
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

    monitors = get_monitors()
    for idx, m in enumerate(monitors):
        print(f"  {idx+1}: x={m.x} y={m.y} w={m.width} h={m.height}")
    try:
        sel = int(input(f"Select AGI's monitor (1-{len(monitors)}) [default=1]: ").strip() or 1)
    except:
        sel = 1
    if 1 <= sel <= len(monitors):
        chosen = monitors[sel-1]
        print(f"AGI will work in monitor zone: x={chosen.x} y={chosen.y} w={chosen.width} h={chosen.height}")

    threading.Thread(target=clipboard_watcher, args=(log_path, token, gist_id), daemon=True).start()
    action_executor(log_path, token, gist_id)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[EXITING]")
