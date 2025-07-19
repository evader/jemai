# synapz_listener_v1.0.py
# JEMAI OS Listener — Version 1.0
# Last Updated: 2025-07-18
# Built by: [AgentName] (pending) for David Lee
"""
Clipboard/command trigger for JEMAI OS.
Listens for defined hotkey or clipboard triggers and queries memory API.
"""

import pyperclip
import requests
import time
import sys

# ---- CONFIG ----
API_USER = "super"
API_PASS = "TechnoAPI69"
API_ENDPOINTS = [
    "http://jemai.local:8089",
    "http://localhost:8089"
]
MAX_RESULTS = 3

TRIGGERS = [
    ("JEMAI-SEARCH::", "memory_search"),
    ("JEMAI-CMD::", "shell"),
    ("JEMAI-GET::", "memory_get"),
    ("JEMAI-NAMEGEN::", "namegen"),
]

def memory_search(query, limit=MAX_RESULTS):
    for api in API_ENDPOINTS:
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
                return results
        except Exception as e:
            print(f"Memory API failed at {api}: {e}", file=sys.stderr)
    return []

def main():
    print("=== Synapz Clipboard Listener v1.0 Started ===")
    print("Watching for triggers:", ", ".join(t[0] for t in TRIGGERS))

    last_clipboard_content = ""
    while True:
        try:
            current_clipboard_content = pyperclip.paste()
            if current_clipboard_content != last_clipboard_content:
                last_clipboard_content = current_clipboard_content
                for trigger, action in TRIGGERS:
                    if current_clipboard_content.startswith(trigger):
                        q = current_clipboard_content[len(trigger):].strip()
                        if action == "memory_search":
                            results = memory_search(q)
                            if results:
                                txt = "\n\n".join(
                                    f"{r['title']} | {r['source']}\n{r['text'][:120].replace(chr(10),' ')}..."
                                    for r in results
                                )
                                pyperclip.copy(txt)
                                print("--- Result copied to clipboard ---")
                            else:
                                pyperclip.copy("No results found.")
                                print("--- No results found ---")
                        elif action == "namegen":
                            import random
                            names = [
                                "Synthmind", "Signalroot", "Pulsekey", "Haloid", "Vectorus",
                                "Quanta", "Fluxel", "Nodeus", "Echotrax", "Originox",
                                "Luminaut", "Machinality", "Datadream", "Memorion", "Glintforge"
                            ]
                            suggestion = random.choice(names)
                            pyperclip.copy(suggestion)
                            print(f"--- Agent name suggestion copied: {suggestion} ---")
                        else:
                            pyperclip.copy("Action not yet implemented.")
                            print("--- Action not yet implemented ---")
                        break
            time.sleep(1)
        except pyperclip.PyperclipException:
            time.sleep(2)
        except Exception as e:
            print(f"Listener error: {e}", file=sys.stderr)
            time.sleep(2)

if __name__ == "__main__":
    main()
