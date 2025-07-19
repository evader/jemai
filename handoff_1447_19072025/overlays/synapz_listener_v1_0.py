# synapz_listener_v1_0.py
# Synapz Clipboard Listener v1.0
# Last Updated: 2025-07-18
# Built by: [AgentName] (pending) for David Lee

import pyperclip
import requests
import time
import sys

# --- Configuration ---
MEMORY_API_URLS = [
    "http://jemai.local:8089",
    "http://localhost:8089"
]
API_USER = "super"
API_PASS = "TechnoAPI69"

TRIGGERS = {
    "JEMAI-SEARCH::": "search",
    "JEMAI-GET::": "get",
    "JEMAI-CMD::": "cmd",
    "JEMAI-ACTION::": "action"
}

def try_memory_api(url, endpoint, query):
    try:
        auth = (API_USER, API_PASS)
        full_url = f"{url}/{endpoint}"
        if endpoint == "search":
            params = {"q": query, "limit": 3}
            r = requests.get(full_url, params=params, auth=auth, timeout=5)
        elif endpoint == "get":
            params = {"idx": int(query)}
            r = requests.get(full_url, params=params, auth=auth, timeout=5)
        else:
            return None
        if r.status_code == 200:
            return r.json()
        else:
            return None
    except Exception:
        return None

def main():
    print("=== Synapz Clipboard Listener Started ===")
    print(f"Watching for triggers: {', '.join(TRIGGERS.keys())}\n")

    last_clip = ""
    while True:
        try:
            clip = pyperclip.paste()
            if clip != last_clip:
                last_clip = clip
                for trigger, action in TRIGGERS.items():
                    if clip.startswith(trigger):
                        content = clip[len(trigger):].strip()
                        print(f"[Listener] {action.title()} command detected: '{content}'")
                        # For demonstration, we just do search/get
                        if action in ["search", "get"]:
                            for url in MEMORY_API_URLS:
                                result = try_memory_api(url, action, content)
                                if result:
                                    print(f"[Listener] Memory API success at {url}")
                                    pyperclip.copy(str(result))
                                    break
                            else:
                                print(f"[Listener] Memory API failed at all URLs.")
                                pyperclip.copy("No results found.")
                        else:
                            print(f"[Listener] No implementation for action '{action}' yet.")
            time.sleep(1)
        except KeyboardInterrupt:
            print("Exiting listener.")
            break
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            time.sleep(2)

if __name__ == "__main__":
    main()
