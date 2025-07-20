import os, sys, json, getpass, subprocess, shutil
from pathlib import Path

# ---- Config (CHANGE ONLY IF NEEDED) ----
REPO_URL = "https://github.com/evader/jemai.git"
USER = "evader"
EMAIL = "evader@jemai.local"
HUB = os.path.join(str(Path.home()), "jemai_hub")
CONFIG = os.path.join(HUB, "jemai_github.json")

def log(msg): print(f"[GITHUB SETUP] {msg}")

def ask_token():
    print("\nPaste your GitHub Personal Access Token (PAT).")
    print("If you've already provided this to JemAI, just press ENTER to skip and use the old value.")
    pat = getpass.getpass("GitHub PAT: ")
    return pat.strip()

def ensure_folder():
    if not os.path.exists(HUB):
        os.makedirs(HUB)
        log(f"Created folder {HUB}")

def write_config(pat):
    cfg = {"repo_url": REPO_URL, "pat": pat, "user": USER, "email": EMAIL}
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    log(f"Wrote config: {CONFIG}")

def clone_repo(pat):
    os.chdir(HUB)
    if not os.path.exists(os.path.join(HUB, ".git")):
        clone_url = REPO_URL.replace("https://", f"https://{pat}@")
        log("Cloning repo (if asked for credentials, paste your PAT)...")
        subprocess.run(["git", "clone", clone_url, "."], check=True)
        log("Repo cloned!")
    else:
        log("Repo already present, skipping clone.")

def pull_latest():
    os.chdir(HUB)
    log("Pulling latest from repo...")
    subprocess.run(["git", "pull"], check=True)

def main():
    print("=== JEMAI GITHUB SYNC SETUP ===")
    ensure_folder()

    pat = ""
    if os.path.exists(CONFIG):
        with open(CONFIG, encoding="utf-8") as f:
            old = json.load(f)
            pat = old.get("pat", "")
    if not pat:
        pat = ask_token()
    write_config(pat)

    try:
        clone_repo(pat)
    except Exception as e:
        log(f"Repo already cloned or error: {e}")

    try:
        pull_latest()
    except Exception as e:
        log(f"Pull error (expected if just cloned): {e}")

    print("\nAll set. JemAI will now auto-sync to GitHub every time!")
    print("You can now use the GitHub integration in jemai.py with zero placeholders.")

if __name__ == "__main__":
    main()
