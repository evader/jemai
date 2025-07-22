import os
import logging
import threading
import time
from ..config import IS_WINDOWS

# Check for TTS libraries during import
try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

try:
    from playsound import playsound
    HAS_PLAYSOUND = True
except ImportError:
    HAS_PLAYSOUND = False


voice_muted = threading.Event()

def speak(text):
    if voice_muted.is_set() or not text: return
    logging.info(f"VOICE: Speaking '{text[:40]}...'")
    
    if HAS_EDGE_TTS and HAS_PLAYSOUND:
        import asyncio
        
        async def _speak_edge():
            voice_file = "jemai_voice.mp3"
            try:
                communicate = edge_tts.Communicate(text, "en-US-JennyNeural")
                with open(voice_file, "wb") as f:
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio": f.write(chunk["data"])
                
                playsound(voice_file)

            except Exception as e: 
                logging.error(f"Edge TTS / playsound failed: {e}")
            finally:
                for i in range(3):
                    try:
                        if os.path.exists(voice_file):
                            os.remove(voice_file)
                        break
                    except PermissionError:
                        time.sleep(0.1)


        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_speak_edge())
        except RuntimeError:
            asyncio.run(_speak_edge())
    else:
        if not HAS_PLAYSOUND:
            logging.warning("playsound library not found. Please run 'pip install -r requirements.txt'.")
        logging.warning("edge-tts not found, falling back to pyttsx3.")
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            logging.error(f"pyttsx3 fallback failed: {e}")
