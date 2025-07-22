import os
import subprocess
from datetime import datetime

HOT_FILES = [
    "run.py",
    "jemai_app/web/routes.py",
    "jemai_app/templates/index.html",
    "jemai_app/core/back_of_house.py",
    "jemai_app/config.py",
    "jemai_app/__init__.py",
    "jemai_app/desktop/clipboard.py",
    "jemai_app/desktop/tray.py",
    # add or remove as you wish
]

def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    return result.stdout.strip()

print("\n=== Repo Status ===\n")
print(run("git status"))

print("\n=== Current Branch & Remotes ===\n")
print(run("git branch -vv"))
print(run("git remote -v"))

print("\n=== Last 10 Commits ===\n")
print(run("git log --oneline -10"))

print("\n=== Diff (last commit) ===\n")
print(run("git diff HEAD~1"))

print("\n=== Uncommitted Changes ===\n")
print(run("git diff"))

print("\n=== Hot File Details ===\n")
for relpath in HOT_FILES:
    abspath = os.path.abspath(relpath)
    print(f"\n--- {relpath} ---")
    if os.path.exists(relpath):
        mtime = datetime.fromtimestamp(os.path.getmtime(relpath))
        print(f"Absolute Path: {abspath}")
        print(f"Last Modified: {mtime}")
        with open(relpath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        max_lines = min(50, len(lines))
        for i in range(max_lines):
            print(f"{i+1:02d}: {lines[i].rstrip()}")
        if len(lines) > max_lines:
            print(f"... ({len(lines)-max_lines} more lines)")
    else:
        print("File not found!")

print("\n=== END OF STATUS ===\n")
