# jemai_app/core/auto_push.py

import subprocess
import threading
import time
import datetime

def auto_git_push_timer(interval_minutes=15):
    while True:
        try:
            status = subprocess.check_output(["git", "status", "--porcelain"], encoding='utf-8')
            if status.strip():
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                subprocess.run(["git", "add", "."], check=True)
                subprocess.run(
                    ["git", "commit", "-m", f"Auto: JemAI periodic snapshot [{now}]"],
                    check=True
                )
                subprocess.run(["git", "push", "origin", "master"], check=True)
                print(f"[AutoPush] Repo updated at {now}")
            else:
                print("[AutoPush] No changes, skipping.")
        except Exception as e:
            print(f"[AutoPush] Error: {e}")
        time.sleep(interval_minutes * 60)

def start_auto_git_push():
    t = threading.Thread(target=auto_git_push_timer, args=(15,), daemon=True)
    t.start()
