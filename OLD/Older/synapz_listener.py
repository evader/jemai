# synapz_listener.py - AI OS Clipboard & Action Listener

import pyperclip
import requests
import time
import datetime
import sys

# --- Configuration ---
API_USER = "super"
API_PASS = "TechnoAPI69"
TRIGGER_PHRASES = {
    "JEMAI-SEARCH::": "search",   # Query memory API
    "JEMAI-GET::": "get",         # Fetch memory by hash
    "JEMAI-CMD::": "shell",       # Local shell (expandable)
    "JEMAI-ACTION::": "agent"     # Send to Synapz or other agents (expandable)
}

def memory_search(query, limit=3):
    apis = [
        "http://jemai.local:8089",
        "http://localhost:8089"
    ]
    for api in apis:
        try:
            resp = requests.get(
                f"{api}/search",
                params={"q": query, "limit": limit},
                auth=(API_USER, API_PASS),
                timeout=8
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if results:
                print(f"Memory API success at {api}")
            else:
                print(f"Memory API success at {api} (no results found)")
            return results
        except Exception as e:
            print(f"Memory API failed at {api}: {e}")
    return []

def copy_to_clipboard(text):
    pyperclip.copy(text)
    print(f"--- Result copied to clipboard ---")

def process_clipboard_content(content):
    for prefix, mode in TRIGGER_PHRASES.items():
        if content.startswith(prefix):
            payload = content[len(prefix):].strip()
            if mode == "search":
                print(f"\n[Listener] JEMAI Memory Search for: '{payload}'")
                results = memory_search(payload)
                if results:
                    formatted = "\n\n".join(
                        [f"Title: {r['title']}\nSource: {r['source']}\n---\n{r['text'][:350]}..." for r in results]
                    )
                    copy_to_clipboard(formatted)
                else:
                    copy_to_clipboard("No results found.")
            elif mode == "get":
                print(f"\n[Listener] JEMAI Memory Get for hash: '{payload}'")
                # Add hash fetch logic here as needed
            elif mode == "shell":
                print(f"\n[Listener] Shell Command (not implemented in this version): '{payload}'")
            elif mode == "agent":
                print(f"\n[Listener] Send to agent (expand as needed): '{payload}'")
            return True
    return False

def main():
    print(f"=== Synapz Clipboard Listener Started ===")
    print(f"Watching for triggers: {', '.join(TRIGGER_PHRASES.keys())}")
    last_clipboard_content = ""
    while True:
        try:
            current = pyperclip.paste()
            if current != last_clipboard_content:
                last_clipboard_content = current
                if not process_clipboard_content(current):
                    pass # Unrecognized trigger, ignore
            time.sleep(1)
        except Exception as e:
            print(f"Listener error: {e}", file=sys.stderr)
            time.sleep(2)

if __name__ == "__main__":
    main()
