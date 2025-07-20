import os
import time
import requests
import openai
from dotenv import load_dotenv

# --- CONFIGURATION ---
GIST_RAW_URL = "https://gist.githubusercontent.com/evader/157e4000aba718d7641a04b5fac5cc66/raw/feedback_store.json"
POLL_INTERVAL = 15  # seconds
GPT_MODEL = "gpt-4"  # Or "gpt-3.5-turbo"

# --- LOAD OPENAI API KEY ---
load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY") or ""

if not OPENAI_KEY:
    print("[FATAL] No OpenAI API key found. Please set OPENAI_API_KEY in your environment or .env file.")
    exit(1)

client = openai.OpenAI(api_key=OPENAI_KEY)

def fetch_gist():
    try:
        r = requests.get(GIST_RAW_URL, timeout=10)
        if r.status_code == 200:
            return r.text
        else:
            print(f"[!] Error fetching gist: {r.status_code}")
            return ""
    except Exception as e:
        print(f"[!] Exception fetching gist: {e}")
        return ""

def ask_gpt(logs):
    try:
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "You are a devops agent and log analyst."},
                {"role": "user", "content": f"Here are the latest agent logs in JSON array format. Summarize the last command's effect and spot any errors, issues, or important results. Output only the summary, no JSON.\n\n{logs}"}
            ],
            max_tokens=500,
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[!] GPT-4 API error: {e}")
        return "[GPT-4 API error]"

def main():
    print("\n--- JEMAI Gist Log Poller & GPT-4 Analyzer ---")
    print(f"Polling logs from: {GIST_RAW_URL}\nModel: {GPT_MODEL}")

    last_logs = ""
    while True:
        logs = fetch_gist()
        if logs and logs != last_logs:
            print("\n[+] New logs found. Sending to GPT-4...")
            result = ask_gpt(logs)
            print("GPT-4:", result)
            last_logs = logs
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting. Bye.")
