import time, subprocess, os, sys, ctypes, json
from threading import Thread
from urllib import request

try:
    import pyperclip
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "pyperclip"])
    import pyperclip

AGENT_NAME = "JEMAI_LtListener"
VERSION = "JEMAI_v3.6-directlink"
LOGFILE = os.path.expanduser(r"~\\jemai_lt_log.txt")
FEEDBACK_FILE = os.path.join(os.getenv("APPDATA"), "JEMAI", "feedback.json")
WEBHOOK_URL = "https://webhook.site/9c1d15ac-37a8-43fb-9206-3f398fe8b877"

os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)

def show_popup(msg):
    MB_OK = 0x0
    MB_TOPMOST = 0x40000
    ctypes.windll.user32.MessageBoxW(0, msg, "JEMAI AGENT", MB_OK | MB_TOPMOST)

def set_autostart():
    import winreg
    key = winreg.HKEY_CURRENT_USER
    path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.OpenKey(key, path, 0, winreg.KEY_SET_VALUE) as reg:
        winreg.SetValueEx(reg, AGENT_NAME, 0, winreg.REG_SZ, f'"{sys.executable}" "{os.path.abspath(__file__)}"')

def post_to_webhook(data: dict):
    try:
        req = request.Request(WEBHOOK_URL, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
        request.urlopen(req, timeout=10)
    except Exception as ex:
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(f"[WEBHOOK ERROR] {ex}\n")

def run_lt_command(command):
    code = command[len("lt::run"):].strip()
    if not code:
        return "[ERROR] No command after lt::run."
    try:
        result = subprocess.run(code, capture_output=True, shell=True, text=True, timeout=30)
        output = result.stdout.strip() + ("\n" + result.stderr.strip() if result.stderr else "")
        if not output.strip():
            output = "[OK] Command ran, no output."

        payload = {
            "agent": AGENT_NAME,
            "version": VERSION,
            "command": code,
            "output": output,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }

        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(f"\n[{payload['timestamp']}] {code}\n{output}\n{'='*32}\n")

        post_to_webhook(payload)
        show_popup(f"Ran: {code}\n\n{output[:3000]}")
        return output
    except Exception as ex:
        err = f"[ERROR] {ex}"
        show_popup(err)
        return err

def clipboard_watcher():
    last = ""
    while True:
        try:
            clip = pyperclip.paste()
            if clip != last and isinstance(clip, str) and clip.strip().lower().startswith("lt::run"):
                run_lt_command(clip.strip())
                last = clip
        except Exception as e:
            with open(LOGFILE, "a", encoding="utf-8") as f:
                f.write(f"[Clipboard error] {e}\n")
        time.sleep(0.5)

def main():
    try:
        set_autostart()
    except Exception as e:
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(f"[Autostart error] {e}\n")
    Thread(target=clipboard_watcher, daemon=True).start()
    show_popup("JEMAI AGENT v3.6-DirectLink is live.\n\nCopy any text starting with lt::run\n\nLogs at:\n" + LOGFILE)
    while True:
        time.sleep(600)

if __name__ == "__main__":
    main()
