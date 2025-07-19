import os
import sys
import shutil
import subprocess
import platform
import time

REPO_URL = "https://github.com/evader/jemai.git"
RAW_PY = "https://raw.githubusercontent.com/evader/jemai/main/jemai.py"
JEMAI_DIR = os.path.join(os.getcwd(), "jemai")
JEMAI_FILE = os.path.join(os.getcwd(), "jemai.py")

def is_tool(name):
    "Check if a tool exists in PATH."
    from shutil import which
    return which(name) is not None

def ensure_tools():
    tools = ["git", "curl"]
    missing = [t for t in tools if not is_tool(t)]
    if missing:
        print(f"[JEMAI-LOADER] Missing required tools: {', '.join(missing)}")
        if platform.system() == "Windows":
            print("Please install missing tools (Git: https://git-scm.com, Curl: Microsoft Store or choco install curl).")
        else:
            print("Try: sudo apt-get install git curl")
        sys.exit(1)

def fetch_jemai_code():
    # Prefer git if available
    if is_tool("git"):
        if os.path.isdir(JEMAI_DIR):
            print("[JEMAI-LOADER] Updating existing jemai repo...")
            subprocess.call(["git", "-C", JEMAI_DIR, "pull"])
        else:
            print("[JEMAI-LOADER] Cloning jemai repo...")
            subprocess.call(["git", "clone", REPO_URL, JEMAI_DIR])
        jemai_path = os.path.join(JEMAI_DIR, "jemai.py")
        if os.path.isfile(jemai_path):
            shutil.copy(jemai_path, JEMAI_FILE)
            print("[JEMAI-LOADER] jemai.py copied from repo.")
            return True
    # Fallback to curl download
    print("[JEMAI-LOADER] Downloading jemai.py directly...")
    rc = os.system(f"curl -L -o \"{JEMAI_FILE}\" \"{RAW_PY}\"")
    return rc == 0 and os.path.isfile(JEMAI_FILE)

def ensure_jemai():
    tries = 3
    for _ in range(tries):
        if os.path.isfile(JEMAI_FILE):
            try:
                # Quick test if file is not empty and looks like Python
                with open(JEMAI_FILE, encoding="utf-8") as f:
                    head = f.read(200)
                    if "def " in head or "import " in head:
                        return True
            except Exception: pass
        fetch_jemai_code()
        time.sleep(2)
    print("[JEMAI-LOADER] Failed to obtain a valid jemai.py.")
    sys.exit(1)

def run_jemai():
    print("[JEMAI-LOADER] Launching jemai.py...")
    py = sys.executable
    folder = os.path.dirname(os.path.abspath(__file__))
    jemai_py = os.path.join(folder, "jemai.py")
    if not os.path.isfile(jemai_py):
        print("[JEMAI-LOADER] ERROR: jemai.py not found in", folder)
        sys.exit(1)
    try:
        # Use subprocess.run to preserve quoting and error codes
        subprocess.run([py, jemai_py])
    except Exception as e:
        print(f"[JEMAI-LOADER] Failed to launch jemai.py: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("=== JEMAI AGI: SUPER LOADER ===")
    ensure_tools()
    ensure_jemai()
    run_jemai()
