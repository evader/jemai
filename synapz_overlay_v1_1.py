# synapz_overlay_v1_1.py
# Synapz Overlay v1.1
# Last Updated: 2025-07-18
# Built by: [AgentName] (pending) for David Lee

import keyboard
import threading
import time
import requests
import pyperclip

MEMORY_API_URLS = [
    "http://jemai.local:8089",
    "http://localhost:8089"
]
API_USER = "super"
API_PASS = "TechnoAPI69"

HOTKEY = "ctrl+shift+space"

def try_memory_api_search(query):
    for url in MEMORY_API_URLS:
        try:
            r = requests.get(f"{url}/search", params={"q": query, "limit": 5}, auth=(API_USER, API_PASS), timeout=5)
            if r.status_code == 200:
                return r.json()
        except:
            continue
    return None

def on_hotkey():
    print("Hotkey triggered! Enter your query:")
    query = input("> ")
    results = try_memory_api_search(query)
    if results and results.get("count", 0) > 0:
        print("Results found:")
        for res in results["results"]:
            print(f"- {res['title']}: {res['text'][:100]}...")
        pyperclip.copy(str(results))
        print("Results copied to clipboard.")
    else:
        print("No results found.")
        pyperclip.copy("No results found.")

def listener():
    print(f"Hotkey listener active! Press {HOTKEY} to launch Synapz overlay.")
    keyboard.add_hotkey(HOTKEY, on_hotkey)
    while True:
        time.sleep(3600)

if __name__ == "__main__":
    listener()
