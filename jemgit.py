import os
import sys
import json
import time
import threading
import subprocess
import requests
import openai

try:
    import pyperclip
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyperclip"])
    import pyperclip

from dotenv import load_dotenv

# ==== CONFIGURATION ====
APP_NAME = "JEMAI"
LOG_FILENAME = "feedback_store.json"
GIST_META = os.path.join(os.path.expanduser("~"), f".{APP_NAME}_gist_meta.json")
CLIPBOARD_PREFIX = "lt::run"
CLIPBOARD_CHECK_INTERVAL = 0.5
GIST_POLL_INTERVAL = 15  # seconds
GIST_RAW_URL = "https://gist.githubusercontent.com/evader/157e4000aba718d7641a04b5fac5cc66/raw/feedback_store.json"
GPT_MODEL = "gpt-4"

# ==== SETUP OPENAI ====
load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY") or ""
if not OPENAI_KEY:
    print("[FATAL] No OpenAI API key found. Please set OPENAI_API_KEY in your environment or .env file.")
    sys.exit(1)
client = openai.OpenAI(api_key=OPENAI_KEY)

# ==== SETUP GITHUB ====
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

# ==== LOGGING ====
def append_log(entry, log_path):
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

# ==== CLIPBOARD COMMAND WATCHER ====
def run_command(command):
    try:
        result = subprocess.run(command, capture_output=True, shell=True, text=True, timeout=90)
        return result.stdout + ("\n" + result.stderr if result.stderr else "")
    except Exception as e:
        return f"[ERROR] {e}"

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

# ==== GPT-4 POLLER + ACTION EXECUTION ====
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

def ask_gpt(logs):
    try:
        prompt = (
            "You are an autonomous DevOps/OS agent. Here is a JSON array of log entries (latest last). "
            "Summarize the most recent action, then ALWAYS suggest a safe next shell command as 'action', even if just 'echo AGI trigger test'. "
            "Respond ONLY in a single JSON object: {\"summary\": \"...\", \"action\": \"<shell_command>\"}."
            "\n\nLOGS:\n" + logs
        )
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[!] GPT-4 API error: {e}")
        return None

def action_poller_and_executor(log_path, token, gist_id):
    last_logs = ""
    while True:
        logs = fetch_gist()
        if logs and logs != last_logs:
            print("\n[+] New logs found. Sending to GPT-4...")
            gpt_response = ask_gpt(logs)
            print("GPT-4:", gpt_response)
            # Try to parse action from response
            try:
                result = json.loads(gpt_response)
                summary = result.get("summary")
                action_cmd = result.get("action")
                if summary:
                    print(f"[SUMMARY] {summary}")
                if action_cmd:
                    print(f"[ACTION] Executing suggested action: {action_cmd}")
                    output = run_command(action_cmd)
                    entry = {
                        "agent": "JEMAI_GistAgent",
                        "command": action_cmd,
                        "output": output,
                        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                        "version": "JEMAI_vGist",
                        "triggered_by": "GPT-4"
                    }
                    append_log(entry, log_path)
                    update_gist(token, gist_id, log_path)
                    print("[ACTION OUTPUT]:", output)
                else:
                    print("[ACTION] No action triggered.")
            except Exception as e:
                print(f"[!] Could not parse GPT-4 action: {e}")
            last_logs = logs
        time.sleep(GIST_POLL_INTERVAL)

# ==== MAIN ====
def main():
    print("--- JEMAI ONE-FILE AGI AGENT ---")
    log_path = os.path.join(os.path.expanduser("~"), LOG_FILENAME)
    if not os.path.exists(log_path):
        with open(log_path, "w") as f:
            f.write("")  # Start empty; JSON array will be built on update
    token = get_token()
    gist_id = get_gist_id(token)
    print(f"Gist will be updated at: https://gist.github.com/{gist_id}")
    print("JEMAI AGI Agent running. Copy 'lt::run <your_command>' to clipboard to execute and upload.")
    threading.Thread(target=clipboard_watcher, args=(log_path, token, gist_id), daemon=True).start()
    action_poller_and_executor(log_path, token, gist_id)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting. Bye.")
