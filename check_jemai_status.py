import os
import subprocess
import tempfile
import shutil
import sys

HOT_FILES = [
    'run.py',
    'jemai_app/web/routes.py',
    'jemai_app/templates/index.html',
]

REPO_URL = "https://github.com/evader/jemai.git"

def run(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return result.stdout.strip()

def main():
    print("\n=== Checking Current Directory ===")
    local_missing = []
    for f in HOT_FILES:
        exists = os.path.exists(f)
        print(f"{f} {'FOUND' if exists else 'NOT FOUND'} in local dir.")
        if not exists:
            local_missing.append(f)

    print("\n=== Checking Latest Remote Repo ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Cloning repo to: {tmpdir}")
        out = run(f"git clone --depth=1 {REPO_URL} .", cwd=tmpdir)
        # List hot files in remote
        remote_missing = []
        for f in HOT_FILES:
            remote_path = os.path.join(tmpdir, f)
            exists = os.path.exists(remote_path)
            print(f"{f} {'FOUND' if exists else 'NOT FOUND'} in remote repo.")
            if not exists:
                remote_missing.append(f)

        print("\n=== Repo Info ===")
        print(run("git status", cwd=tmpdir))
        print("\n* Last 5 commits:")
        print(run("git log --oneline -5", cwd=tmpdir))

        if remote_missing:
            print("\nFiles missing in remote repo:")
            for f in remote_missing:
                print(f"  - {f}")
            print("\nLikely fix: Commit and push these files from your local working directory.")

    print("\nDone.")

if __name__ == "__main__":
    main()
