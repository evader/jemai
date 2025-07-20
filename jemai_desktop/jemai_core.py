import os, sys, json, logging
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import webbrowser

# === Config ===
LOG_PATH = os.path.join(os.path.dirname(__file__), "jemai.log")
logging.basicConfig(filename=LOG_PATH, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# === Voice (Edge TTS, cross-platform, fallback to system) ===
try:
    import edge_tts
    HAS_EDGE = True
except ImportError:
    HAS_EDGE = False

from threading import Event
voice_muted = Event()
voice_muted.set()

def speak(text):
    if voice_muted.is_set():
        return
    if HAS_EDGE:
        import asyncio
        async def _speak():
            communicate = edge_tts.Communicate(text, "en-US-JennyNeural")
            await communicate.save("voice.mp3")
            if sys.platform == "win32":
                os.system('start /min wmplayer voice.mp3')
            elif sys.platform == "darwin":
                os.system('afplay voice.mp3 &')
            else:
                os.system('mpg123 voice.mp3 &')
        asyncio.run(_speak())
    else:
        # fallback: system say command
        if sys.platform == "win32":
            os.system(f"powershell -c \"Add-Type –AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{text}')\"")
        elif sys.platform == "darwin":
            os.system(f"say '{text}'")
        else:
            os.system(f"espeak '{text}'")

def toggle_voice():
    if voice_muted.is_set():
        voice_muted.clear()
        speak("Voice assistant enabled. Hello, Dave.")
    else:
        voice_muted.set()
        print("Voice muted.")

# === F-Keys Mapping (simple file-based) ===
FKEYS_PATH = os.path.join(os.path.dirname(__file__), "fkeys.json")
def load_fkeys():
    try: return json.load(open(FKEYS_PATH))
    except: return {}
def save_fkeys(keys):
    json.dump(keys, open(FKEYS_PATH, "w"))

# === API ===
class Handler(BaseHTTPRequestHandler):
    def _resp(self, d): self.send_response(200); self.send_header('Content-type','application/json'); self.end_headers(); self.wfile.write(json.dumps(d).encode())
    def do_POST(self):
        ln = int(self.headers['Content-Length'])
        data = self.rfile.read(ln).decode()
        req = json.loads(data)
        if self.path == "/api/chat":
            q = req.get("q","")
            resp = process_chat(q)
            self._resp({"resp": resp})
        elif self.path == "/api/voice_toggle":
            toggle_voice()
            self._resp({"resp":"Voice toggled."})
        else:
            self._resp({"resp":"Unknown API"})

def process_chat(q):
    if q.strip().lower() == "open logs":
        webbrowser.open(LOG_PATH)
        return "Opened log file."
    if q.strip().lower().startswith("set f"):
        k, cmd = q[4:7], q[8:]
        fkeys = load_fkeys(); fkeys[k]=cmd; save_fkeys(fkeys)
        return f"Set {k} to {cmd}"
    # Call local LLM (simulate or hook to OpenAI, Gemini, etc.)
    try:
        import openai
        openai.api_key = os.getenv("OPENAI_API_KEY")
        res = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role":"system","content":"You are JEMAI, an expert coder, system admin, and assistant."},{"role":"user","content":q}],
            max_tokens=512,
        )
        resp = res["choices"][0]["message"]["content"]
        if not voice_muted.is_set(): speak(resp)
        return resp
    except Exception as e:
        logging.exception(e)
        return f"[Error]: {e}"

def run():
    print("Starting JEMAI backend...")
    server = HTTPServer(('localhost',8181), Handler)
    print("Ready at http://localhost:8181")
    server.serve_forever()

if __name__ == "__main__":
    run()
