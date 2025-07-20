import os, sys, subprocess, threading, time, shutil, datetime, platform, json

JEMAI_HUB = os.path.abspath(os.path.join(os.path.dirname(__file__), "jemai_hub"))
AI_JOBS = os.path.join(JEMAI_HUB, "ai_jobs")
LOGS_DIR = os.path.join(JEMAI_HUB, "autorun_logs")
VERSIONS_DIR = os.path.join(JEMAI_HUB, ".jemai_versions")
JEMAI_MAIN = os.path.join(os.getcwd(), "jemai.py")
GIT_REMOTE = "origin"
GIT_BRANCH = "main"

os.makedirs(AI_JOBS, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(VERSIONS_DIR, exist_ok=True)

def logit(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(LOGS_DIR, "autorun.log"), "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"[AUTORUN] {msg}")

def backup_version():
    if not os.path.exists(JEMAI_MAIN): return
    stamp = datetime.datetime.now().strftime("%d-%m-%Y-%H%M%S")
    dest = os.path.join(VERSIONS_DIR, f"jemai_{stamp}.py")
    shutil.copy(JEMAI_MAIN, dest)
    logit(f"Backed up jemai.py to {dest}")

def run_code_file(path):
    ext = os.path.splitext(path)[1].lower()
    result = ""
    try:
        if ext == ".py":
            logit(f"Running {path}")
            proc = subprocess.run([sys.executable, path], capture_output=True, timeout=120, text=True)
            result = proc.stdout + "\n" + proc.stderr
        elif ext in [".bat", ".cmd"]:
            logit(f"Running {path} (cmd)")
            proc = subprocess.run([path], capture_output=True, timeout=120, text=True, shell=True)
            result = proc.stdout + "\n" + proc.stderr
        elif ext == ".sh":
            logit(f"Running {path} (bash)")
            proc = subprocess.run(["bash", path], capture_output=True, timeout=120, text=True)
            result = proc.stdout + "\n" + proc.stderr
        elif ext == ".sql":
            logit(f"SQL file {path} detected (bake-in to db with your code).")
            result = "SQL file detected, not auto-run."
        elif ext == ".json":
            logit(f"JSON file {path} imported.")
            result = "JSON file imported, not auto-run."
        else:
            logit(f"Unhandled file {path}")
            result = f"Unhandled filetype: {ext}"
    except Exception as e:
        result = f"ERROR: {e}"
    # Write run log
    with open(os.path.join(LOGS_DIR, f"run_{os.path.basename(path)}_{int(time.time())}.log"), "w", encoding="utf-8") as f:
        f.write(result)
    return result

def git_commit_push(msg="Auto commit by autorun"):
    logit("Committing and pushing to git...")
    try:
        subprocess.call(["git", "add", "."])
        subprocess.call(["git", "commit", "-am", msg])
        subprocess.call(["git", "push", GIT_REMOTE, GIT_BRANCH])
        logit("Git push complete.")
    except Exception as e:
        logit(f"Git push failed: {e}")

def autorun_loop():
    logit("JEMAI autorun is watching ai_jobs...")
    while True:
        files = [f for f in os.listdir(AI_JOBS) if not f.startswith("._")]
        for fname in files:
            path = os.path.join(AI_JOBS, fname)
            if not os.path.isfile(path): continue
            # Process file!
            out = run_code_file(path)
            backup_version()
            # If jemai.py modified, restart/reload if needed!
            if fname == "jemai.py":
                logit("jemai.py replaced! Backing up and restarting.")
                shutil.copy(path, JEMAI_MAIN)
                git_commit_push(f"jemai.py auto-replaced by autorun: {datetime.datetime.now().isoformat()}")
                # Try to restart jemai.py (simple way)
                if platform.system() == "Windows":
                    os.system(f'start /min python "{JEMAI_MAIN}"')
                else:
                    subprocess.Popen([sys.executable, JEMAI_MAIN])
            else:
                git_commit_push(f"Ran {fname} via autorun.")
            # Move processed files to logs (archive)
            arch = os.path.join(LOGS_DIR, f"done_{os.path.basename(path)}_{int(time.time())}")
            shutil.move(path, arch)
            logit(f"Moved {fname} to {arch}")
        time.sleep(3)

if __name__ == "__main__":
    logit("=== Starting JEMAI AUTORUN ===")
    autorun_loop()
