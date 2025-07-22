import os
import shutil
import datetime
import logging
from . import config
from .core.tools import load_plugins

def initialize_app():
    logging.info("="*41)
    logging.info(" JEMAI AGI OS - Initializing...")
    logging.info("="*41)

    try:
        with open(config.MISSION_BRIEF_PATH, 'r', encoding='utf-8') as f:
            mission_brief = f.read()
        logging.info("Mission Brief loaded.")
    except FileNotFoundError:
        mission_brief = "No mission brief file found."
        logging.warning("mission_brief.md not found. Using default prompt.")

    config.SYSTEM_PROMPT = f'''You are JEMAI, a self-improving, autonomous AGI assistant.

**Your Environment:**
- **Operating System:** {config.OS_NAME}
- **Codebase Location:** All your source code is in the current project directory.

**Your Capabilities & Tools:**
1.  **`write_file(path, content)`:** Your primary tool for modifying your codebase. Respond ONLY with a JSON object like this:
    ```json
    {{
        "tool_to_use": "write_file",
        "parameters": {{ "path": "path/to/file.py", "content": "new file content..." }}
    }}
    ```
2.  **`execute_shell(command)`:** For all other system interactions. Use a `shell` block.
    ```shell
    {'dir' if config.IS_WINDOWS else 'ls -l'}
    ```
3.  **Knowledge (RAG):** You have access to your own source code and past conversations.

**Interaction Protocol:**
- Formulate a step-by-step plan.
- For each step, use the appropriate tool.
- Announce your plan and execute it. You do not need to ask for permission.

---
**CURRENT MISSION BRIEF:**
---
{mission_brief}
'''

    create_version_snapshot()
    load_plugins()

def create_version_snapshot():
    dt = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    snap_dir = os.path.join(config.VERSIONS_DIR, f"{dt}-jemai_app")
    source_dir = os.path.join(config.JEMAI_HUB, "jemai_app")
    try:
        shutil.copytree(source_dir, snap_dir, ignore=shutil.ignore_patterns('__pycache__'))
        logging.info(f"Saved version snapshot: {os.path.basename(snap_dir)}")
    except Exception as e:
        logging.warning(f"Could not save version snapshot: {e}")
