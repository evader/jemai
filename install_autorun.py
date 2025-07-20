import os, sys, platform, shutil, subprocess, getpass

JEMAI_DIR = os.path.abspath(os.path.dirname(__file__))
BAT_FILE = os.path.join(JEMAI_DIR, "start_jemai.bat")
SH_FILE = os.path.join(JEMAI_DIR, "start_jemai.sh")
PY_FILE = os.path.join(JEMAI_DIR, "jemai.py")

def ensure_bat():
    if not os.path.isfile(BAT_FILE):
        with open(BAT_FILE, "w") as f:
            f.write(f'@echo off\ncd /d "{JEMAI_DIR}"\npython jemai.py\n')
    print(f"[JEMAI] Batch file ready at {BAT_FILE}")

def ensure_sh():
    if not os.path.isfile(SH_FILE):
        with open(SH_FILE, "w") as f:
            f.write(f'#!/bin/bash\ncd "{JEMAI_DIR}"\npython3 jemai.py\n')
        os.chmod(SH_FILE, 0o755)
    print(f"[JEMAI] Shell script ready at {SH_FILE}")

def setup_win_autorun():
    startup_dir = os.path.join(os.environ["APPDATA"], "Microsoft\\Windows\\Start Menu\\Programs\\Startup")
    dest = os.path.join(startup_dir, "start_jemai.bat")
    ensure_bat()
    shutil.copyfile(BAT_FILE, dest)
    print(f"[JEMAI] Autorun installed! (Windows Startup Folder)\n    {dest}")

def setup_linux_autorun():
    ensure_sh()
    cron_line = f"@reboot {SH_FILE}"
    # Only add if not present
    out = subprocess.getoutput("crontab -l")
    if cron_line not in out:
        subprocess.run(f'(crontab -l; echo "{cron_line}") | sort -u | crontab -', shell=True)
        print("[JEMAI] Autorun installed! (crontab @reboot)")
    else:
        print("[JEMAI] Autorun already present in crontab.")

def main():
    sys.stdout.write("=== JEMAI AUTORUN INSTALLER ===\n")
    if not os.path.isfile(PY_FILE):
        print(f"[ERROR] Cannot find jemai.py in {JEMAI_DIR}")
        sys.exit(1)
    sys.stdout.write(f"Detected OS: {platform.system()}\n")
    if platform.system() == "Windows":
        setup_win_autorun()
    elif platform.system() in ("Linux", "Darwin"):
        setup_linux_autorun()
    else:
        print("[JEMAI] Sorry, autorun install only supports Windows and Linux for now.")

if __name__ == "__main__":
    main()
