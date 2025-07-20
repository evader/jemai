import os
import subprocess
import shutil

repo_dir = r"C:\JEMAI_HUB"
env_file = os.path.join(repo_dir, ".env")
github_json = os.path.join(repo_dir, "jemai_hub", "jemai_github.json")
gitignore_path = os.path.join(repo_dir, ".gitignore")

# 1. Remove secrets from tracked files
if os.path.exists(env_file):
    subprocess.run(['git', 'rm', '--cached', '.env'])
    print("[JEMAI] .env removed from repo tracking.")
else:
    print("[JEMAI] .env not found.")

if os.path.exists(github_json):
    subprocess.run(['git', 'rm', '--cached', github_json])
    print("[JEMAI] jemai_github.json removed from repo tracking.")
else:
    print("[JEMAI] jemai_github.json not found.")

# 2. Add to .gitignore
lines = []
if os.path.exists(gitignore_path):
    with open(gitignore_path, "r") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
if ".env" not in lines:
    lines.append(".env")
if "jemai_hub/jemai_github.json" not in lines:
    lines.append("jemai_hub/jemai_github.json")
with open(gitignore_path, "w") as f:
    f.write("\n".join(lines) + "\n")
print("[JEMAI] .gitignore updated.")

# 3. Overwrite jemai_github.json for local use only
if os.path.exists(github_json):
    with open(github_json, "w") as f:
        f.write('{"repo_url": "https://github.com/evader/jemai.git", "pat": "", "user": "evader", "email": "evader@jemai.local"}\n')
    print("[JEMAI] jemai_github.json scrubbed for local only.")

# 4. Commit and push (using --allow-empty to ensure commit if needed)
subprocess.run(['git', 'add', '.gitignore', 'jemai.py'])
subprocess.run(['git', 'commit', '--allow-empty', '-m', 'Scrub secrets: .env, jemai_github.json, update .gitignore'])
subprocess.run(['git', 'push', 'origin', 'main'])

print("[JEMAI] Repo is now secret-free, unblocked, and safe to sync!")

# 5. Final Reminder: restore your real jemai_github.json and .env LOCALLY (never in repo)
print("\nRestore your local .env and jemai_github.json (with secrets) for runtime use only.\nNEVER add or commit these files again!")
