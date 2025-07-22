import sys
import subprocess
import os
import shutil
import logging
import time

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger()

VENV = "venv"
REQ = "requirements.txt"

# Set target versions
PIP_VERSION = "23.3.1"
SETUPTOOLS_VERSION = "68.2.2"

def find_python311():
    # Add more if needed
    paths = [
        r"C:\Program Files\Python311\python.exe",
        r"C:\Python311\python.exe"
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    logger.error("Python 3.11 not found. Please install Python 3.11.x.")
    sys.exit(1)

def run(cmd, env=None):
    logger.info(" ".join(cmd))
    try:
        subprocess.check_call(cmd, env=env)
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {cmd} ({e})")
        sys.exit(1)

def remove_venv():
    if os.path.exists(VENV):
        logger.info(f"Removing {VENV}...")
        # If venv is busy, retry after delay
        for i in range(5):
            try:
                shutil.rmtree(VENV)
                logger.info("Venv removed.")
                return
            except Exception as ex:
                logger.warning(f"Venv removal failed: {ex} (retry {i+1}/5)")
                time.sleep(3)
        logger.error("Could not remove venv after multiple retries.")
        sys.exit(1)

def main():
    py = find_python311()

    remove_venv()
    run([py, "-m", "venv", VENV])

    # Use venv python/pip
    venv_python = os.path.join(VENV, "Scripts", "python.exe")
    venv_pip = os.path.join(VENV, "Scripts", "pip.exe")

    # Down/up-grade pip/setuptools to safe versions
    run([venv_python, "-m", "pip", "install", f"pip=={PIP_VERSION}", f"setuptools=={SETUPTOOLS_VERSION}"])

    # (Optional) Wheel for speed
    run([venv_pip, "install", "--upgrade", "wheel"])

    # Uninstall any potentially broken deps
    run([venv_pip, "uninstall", "-y", "numpy", "chromadb", "chroma-hnswlib", "pydantic", "pydantic_core"])

    # Install your requirements
    if not os.path.exists(REQ):
        logger.error(f"{REQ} not found.")
        sys.exit(1)
    run([venv_pip, "install", "-r", REQ])

    # Validate core modules
    for mod in ["numpy", "pydantic", "chromadb"]:
        try:
            subprocess.check_call([venv_python, "-c", f"import {mod}"])
            logger.info(f"Module {mod} imported successfully.")
        except Exception as e:
            logger.error(f"Module {mod} failed: {e}")
            sys.exit(1)

    logger.info("All done! Activate your venv and run your app.")

if __name__ == "__main__":
    main()
