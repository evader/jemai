import os
import sys
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox
import keyboard
import sounddevice as sd
import soundfile as sf
import edge_tts
import speech_recognition as sr

# -- SETTINGS
JEMAI_SPEAKER = "en-AU-NatashaNeural"   # Sexy female AU voice
JEMAI_API_URL = "http://localhost:8181/api/chat"
HISTORY_FILE = os.path.expanduser("~/.jemai_voice_history.txt")
HOTKEYS = {f"F{i}": "" for i in range(1, 13)}   # F1-F12

class JemaiVoiceUI:
    def __init__(self, root):
        self.root = root
        self.speaking = False
        self.hotkey_config = HOTKEYS.copy()
        self.make_ui()
        self._register_hotkeys()
        self.queue = queue.Queue()
        self.listening_thread = threading.Thread(target=self.listen_loop, daemon=True)
        self.listening_thread.start()
        self.speaker_enabled = tk.BooleanVar(value=True)
        self.overlay = None

    def make_ui(self):
        self.root.title("JEMAI AGI Voice Assistant")
        self.root.geometry("440x380")
        self.root.configure(bg="#161616")
        title = ttk.Label(self.root, text="🎤 JEMAI Voice", font=("Segoe UI", 19, "bold"), background="#161616", foreground="#F8B195")
        title.pack(pady=(12, 4))
        self.text = tk.Text(self.root, height=12, width=50, bg="#222", fg="#F8B195", insertbackground="#fff")
        self.text.pack(padx=16, pady=6)
        self.speaker_btn = ttk.Button(self.root, text="🔊 Speaker: On", command=self.toggle_speaker)
        self.speaker_btn.pack(pady=6)
        self.listen_btn = ttk.Button(self.root, text="🎙️ Speak to JEMAI", command=self.listen_once)
        self.listen_btn.pack(pady=6)
        hotkey_btn = ttk.Button(self.root, text="Show Hotkey Overlay", command=self.show_hotkey_overlay)
        hotkey_btn.pack(pady=(6, 2))
        ttk.Label(self.root, text="F1–F12 = Custom actions (edit below)", background="#161616", foreground="#aaa").pack()
        self.load_history()

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                lines = f.read()
                self.text.insert(tk.END, lines)

    def save_history(self, msg):
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")

    def toggle_speaker(self):
        self.speaker_enabled.set(not self.speaker_enabled.get())
        self.speaker_btn.config(text="🔊 Speaker: On" if self.speaker_enabled.get() else "🔇 Speaker: Muted")

    def listen_once(self):
        self.text.insert(tk.END, "\n[Listening...]\n")
        self.root.update()
        threading.Thread(target=self._listen_and_send, daemon=True).start()

    def listen_loop(self):
        while True:
            event = self.queue.get()
            if event == "listen":
                self._listen_and_send()

    def _listen_and_send(self):
        try:
            r = sr.Recognizer()
            with sr.Microphone() as source:
                audio = r.listen(source, timeout=8)
            q = r.recognize_google(audio)
            self.text.insert(tk.END, f"\nYou: {q}\n")
            self.save_history(f"You: {q}")
            self.root.update()
            import requests
            resp = requests.post(JEMAI_API_URL, json={"q": q})
            msg = resp.json().get("resp", "[no response]")
            self.text.insert(tk.END, f"JEMAI: {msg}\n")
            self.save_history(f"JEMAI: {msg}")
            self.root.update()
            if self.speaker_enabled.get():
                asyncio.run(self.speak(msg))
        except Exception as e:
            self.text.insert(tk.END, f"[Error: {e}]\n")
            self.root.update()

    async def speak(self, text):
        if not text.strip(): return
        tts = edge_tts.Communicate(text, JEMAI_SPEAKER)
        file = "jemai_tmp.wav"
        await tts.save(file)
        data, fs = sf.read(file, dtype='float32')
        sd.play(data, fs)
        sd.wait()
        os.remove(file)

    def _register_hotkeys(self):
        for i in range(1, 13):
            keyboard.add_hotkey(f"ctrl+f{i}", lambda n=i: self._hotkey_action(n))

    def _hotkey_action(self, n):
        action = self.hotkey_config.get(f"F{n}", "")
        if action:
            self.text.insert(tk.END, f"\n[Hotkey F{n}: {action}]\n")
            import requests
            try:
                resp = requests.post(JEMAI_API_URL, json={"q": action})
                msg = resp.json().get("resp", "[no response]")
                self.text.insert(tk.END, f"JEMAI: {msg}\n")
                if self.speaker_enabled.get():
                    asyncio.run(self.speak(msg))
            except Exception as e:
                self.text.insert(tk.END, f"[Hotkey error: {e}]\n")
            self.root.update()
        else:
            self.text.insert(tk.END, f"\n[Hotkey F{n} not set]\n")
            self.root.update()

    def show_hotkey_overlay(self):
        if self.overlay and self.overlay.winfo_exists():
            self.overlay.lift()
            return
        ov = tk.Toplevel(self.root)
        ov.title("JEMAI Hotkey Overlay")
        ov.geometry("360x340+100+100")
        ov.configure(bg="#181926")
        for i in range(1, 13):
            f = tk.Frame(ov, bg="#181926")
            f.pack(pady=3)
            lbl = tk.Label(f, text=f"F{i}", font=("Segoe UI", 15, "bold"), bg="#181926", fg="#FC618D")
            lbl.pack(side="left", padx=(10,8))
            entry = tk.Entry(f, width=24)
            entry.insert(0, self.hotkey_config.get(f"F{i}", ""))
            entry.pack(side="left", padx=4)
            btn = tk.Button(f, text="Set", command=lambda e=entry, n=i: self.set_hotkey(n, e.get()))
            btn.pack(side="left", padx=6)
        ov.attributes("-topmost", True)
        self.overlay = ov

    def set_hotkey(self, n, val):
        self.hotkey_config[f"F{n}"] = val
        self.text.insert(tk.END, f"\n[Set F{n}: {val}]\n")
        self.root.update()

if __name__ == "__main__":
    import asyncio
    root = tk.Tk()
    ui = JemaiVoiceUI(root)
    root.mainloop()
