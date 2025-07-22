import os
import platform
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

IS_WINDOWS = platform.system() == "Windows"
OS_NAME = platform.system()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
JEMAI_PORT = int(os.getenv("JEMAI_PORT", 8181))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() in ['true', '1', 't']
TRIGGER_PREFIX = "j::"

SYSTEM_PROMPT = "" # Dynamically populated by main.py

JEMAI_HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS_DIR = os.path.join(JEMAI_HUB, "plugins")
VERSIONS_DIR = os.path.join(JEMAI_HUB, "versions")
CHROMA_PATH = os.path.join(JEMAI_HUB, "chroma_db")
TEMPLATES_DIR = os.path.join(JEMAI_HUB, "templates")
MISSION_BRIEF_PATH = os.path.join(JEMAI_HUB, "mission_brief.md")

for d in [PLUGINS_DIR, VERSIONS_DIR, CHROMA_PATH, TEMPLATES_DIR]:
    os.makedirs(d, exist_ok=True)
