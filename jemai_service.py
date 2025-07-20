import threading, time, subprocess, tkinter as tk, json, os, queue, re, logging, win32clipboard, sys
from tkinter import simpledialog, messagebox, ttk
import subprocess, os, sys, time, threading, tkinter as tk, queue, json, logging, win32clipboard
from PIL import Image, ImageDraw
import pystray
from pynput import keyboard as pk

# --------- CONFIG ---------
APPS_TO_LAUNCH = [
    r"explorer.exe",
    r"cmd.exe",
    r"C:\Program Files\Microsoft VS Code\Code.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    # Add more full paths here as you want, or leave only those you use
]

TESSERACT_PATHS = [
    r"C:\JEMAI_HUB\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    # Add more guesses if needed
]

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".jemai_hotkeys.json")
STARTUP_FOLDER = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
SHORTCUT_PATH = os.path.join(STARTUP_FOLDER, "JemaiAGI.lnk")
TRAY_TOOLTIP = "JEMAI AGI Service"
CLIPBOARD_POLL_SECONDS = 1.0
OVERLAY_HIDE_DELAY = 2200

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
def log(msg): logging.info(msg)

def launch_apps():
    for app in APPS_TO_LAUNCH:
        try:
            subprocess.Popen(app, shell=True)
            log(f"[APPS] Launched: {app}")
        except Exception as e:
            log(f"[APPS] Failed: {app} ({e})")

def try_add_tesseract_to_path():
    for tess in TESSERACT_PATHS:
        dir_ = os.path.dirname(tess)
        if os.path.isfile(tess):
            env_path = os.environ.get("PATH", "")
            if dir_ not in env_path:
                os.environ["PATH"] = env_path + ";" + dir_
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Environment', 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, 'PATH', 0, winreg.REG_EXPAND_SZ, os.environ["PATH"])
                log(f"[TESSERACT] Path added to user PATH: {dir_}")
            except Exception as e:
                log(f"[TESSERACT] Warning: Could not set user PATH: {e}")
            return True
    log("[TESSERACT] Not found, skipping PATH setup.")
    return False

class JemaiOverlay(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JEMAI Command Status")
        self.geometry("480x120+100+40")
        self.resizable(False, False)
        self.configure(bg="#222")
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self.hide)
        self.label = tk.Label(self, text="Status: Idle", font=("Segoe UI", 15), bg="#222", fg="#fff", justify="left")
        self.label.pack(fill="both", expand=True, padx=14, pady=12)
        self.status = "idle"
        self.proc = None
        self.after_id = None
        self.bind("<Escape>", lambda e: self.cancel())
        self.bind("<F1>", lambda e: self.cancel())
        self.withdraw()
        self.ui_queue = queue.Queue()
        self.after(100, self.process_ui_queue)
    def process_ui_queue(self):
        while not self.ui_queue.empty():
            func, args = self.ui_queue.get()
            func(*args)
        self.after(100, self.process_ui_queue)
    def safe_update_label(self, text):
        self.ui_queue.put((self.label.config, ({"text": text},)))
    def safe_show(self):
        self.ui_queue.put((self._show, ()))
    def _show(self):
        self.deiconify()
        self.lift()
        self.focus_force()
        self.status = "active"
    def show(self, msg="Status: Idle"):
        self.safe_update_label(msg)
        self.safe_show()
    def hide(self):
        self.withdraw()
        self.status = "idle"
    def running(self, cmd):
        self.safe_update_label(f"Running: {cmd}\nESC/F1=Cancel")
        self.safe_show()
        self.status = "running"
    def done(self, output):
        display = output[:100].replace("\n", " ") if output else "No output"
        self.safe_update_label(f"Done!\n{display} ...")
        if self.after_id: self.after_cancel(self.after_id)
        self.after_id = self.after(OVERLAY_HIDE_DELAY, self.hide)
        self.status = "done"
    def cancel(self):
        if self.proc and self.status == "running":
            self.safe_update_label("Cancelling...")
            try: self.proc.terminate()
            except: pass
            self.status = "cancelled"
            if self.after_id: self.after_cancel(self.after_id)
            self.after_id = self.after(1000, self.hide)

def run_command(cmd, overlay, source):
    log(f"[{source}] RUN: {cmd}")
    try:
        overlay.running(cmd)
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        overlay.proc = proc
        output = ""
        for line in iter(proc.stdout.readline, b''):
            if not line: break
            output += line.decode(errors="ignore")
            overlay.safe_update_label(f"Running: {cmd}\n{output[-80:]}\nESC/F1=Cancel")
            if overlay.status == "cancelled":
                try: proc.terminate()
                except: pass
                break
        proc.wait()
        overlay.done(output)
        overlay.proc = None
        log(f"[{source}] DONE: {cmd}")
    except Exception as e:
        overlay.safe_update_label(f"Error: {e}")
        log(f"[{source}] ERROR running command: {e}")

class HotkeyManager:
    def __init__(self, overlay):
        self.overlay = overlay
        self.enabled = True
        self.hotkeys = {}
        self.load_config()
        self.listener = None
        self.register_all_hotkeys()
    def load_config(self):
        try:
            if os.path.isfile(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.hotkeys = data.get("hotkeys", {})
                    self.enabled = data.get("enabled", True)
                    log("[CONFIG] Hotkeys loaded")
            else:
                self.hotkeys = {
                    "f1": "notepad",
                    "f2": "calc",
                    "f3": "start https://github.com/evader/jemai",
                    "f4": "dir",
                }
                self.enabled = True
                self.save_config()
        except Exception as e:
            log(f"[CONFIG] Failed to load config: {e}")
    def save_config(self):
        try:
            data = {"hotkeys": self.hotkeys, "enabled": self.enabled}
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            log("[CONFIG] Hotkeys saved")
        except Exception as e:
            log(f"[CONFIG] Failed to save config: {e}")
    def on_press(self, key):
        if not self.enabled: return
        try:
            key_name = None
            if isinstance(key, pk.KeyCode): key_name = key.char
            elif isinstance(key, pk.Key): key_name = str(key).split('.')[-1]
            if key_name and key_name.lower() in self.hotkeys:
                cmd = self.hotkeys[key_name.lower()]
                threading.Thread(target=run_command, args=(cmd, self.overlay, "HOTKEY-"+key_name.upper()), daemon=True).start()
        except: pass
    def register_all_hotkeys(self):
        if self.listener: self.listener.stop()
        self.listener = pk.Listener(on_press=self.on_press)
        self.listener.start()
        log(f"[HOTKEY] Registered hotkeys: {list(self.hotkeys.keys())}")
    def enable(self):
        self.enabled = True
        self.save_config()
        log("[HOTKEY] Service enabled")
    def disable(self):
        self.enabled = False
        self.save_config()
        log("[HOTKEY] Service disabled")
    def trigger_command(self, cmd, source):
        if self.enabled:
            threading.Thread(target=run_command, args=(cmd, self.overlay, source), daemon=True).start()
        else:
            log("[HOTKEY] Trigger ignored, service disabled")
    def open_config_gui(self):
        HotkeyConfigGUI(self).show()
    def stop(self):
        if self.listener: self.listener.stop()

class HotkeyConfigGUI(tk.Toplevel):
    def __init__(self, manager: HotkeyManager):
        super().__init__()
        self.title("JEMAI Hotkey Configuration")
        self.geometry("480x320+150+150")
        self.manager = manager
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(self, columns=("Key", "Command"), show="headings", selectmode="browse")
        self.tree.heading("Key", text="Hotkey")
        self.tree.heading("Command", text="Command")
        self.tree.grid(row=0, column=0, sticky="nsew")
        btn_frame = tk.Frame(self)
        btn_frame.grid(row=1, column=0, sticky="ew", pady=10)
        btn_frame.columnconfigure((0,1,2), weight=1)
        self.btn_add = tk.Button(btn_frame, text="Add Hotkey", command=self.add_hotkey)
        self.btn_add.grid(row=0, column=0, sticky="ew", padx=5)
        self.btn_edit = tk.Button(btn_frame, text="Edit Selected", command=self.edit_selected)
        self.btn_edit.grid(row=0, column=1, sticky="ew", padx=5)
        self.btn_delete = tk.Button(btn_frame, text="Delete Selected", command=self.delete_selected)
        self.btn_delete.grid(row=0, column=2, sticky="ew", padx=5)
        self.refresh_tree()
    def refresh_tree(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for k, v in self.manager.hotkeys.items():
            self.tree.insert("", "end", iid=k, values=(k, v))
    def add_hotkey(self):
        dlg = HotkeyEditDialog(self, "", "")
        self.wait_window(dlg)
        if dlg.result:
            key, cmd = dlg.result
            if key in self.manager.hotkeys:
                messagebox.showerror("Error", "Hotkey already exists.")
                return
            self.manager.hotkeys[key] = cmd
            self.manager.save_config()
            self.manager.register_all_hotkeys()
            self.refresh_tree()
    def edit_selected(self):
        sel = self.tree.selection()
        if not sel: return
        key = sel[0]
        current_cmd = self.manager.hotkeys.get(key, "")
        dlg = HotkeyEditDialog(self, key, current_cmd, edit_key=False)
        self.wait_window(dlg)
        if dlg.result:
            _, new_cmd = dlg.result
            self.manager.hotkeys[key] = new_cmd
            self.manager.save_config()
            self.manager.register_all_hotkeys()
            self.refresh_tree()
    def delete_selected(self):
        sel = self.tree.selection()
        if not sel: return
        key = sel[0]
        if messagebox.askyesno("Confirm Delete", f"Delete hotkey '{key}'?"):
            del self.manager.hotkeys[key]
            self.manager.save_config()
            self.manager.register_all_hotkeys()
            self.refresh_tree()
    def show(self):
        self.grab_set()
        self.focus_set()
        self.wait_window(self)

class HotkeyEditDialog(simpledialog.Dialog):
    def __init__(self, parent, key, command, edit_key=True):
        self.key = key
        self.command = command
        self.edit_key = edit_key
        super().__init__(parent, title="Edit Hotkey")
    def body(self, frame):
        tk.Label(frame, text="Hotkey (e.g. f5, a, b, c):").grid(row=0, column=0, sticky="w")
        self.key_entry = tk.Entry(frame, width=30)
        self.key_entry.grid(row=0, column=1, sticky="ew")
        if not self.edit_key:
            self.key_entry.insert(0, self.key)
            self.key_entry.config(state='disabled')
        else:
            self.key_entry.insert(0, self.key)
        tk.Label(frame, text="Command to run:").grid(row=1, column=0, sticky="w")
        self.cmd_entry = tk.Entry(frame, width=50)
        self.cmd_entry.grid(row=1, column=1, sticky="ew")
        self.cmd_entry.insert(0, self.command)
        return self.key_entry
    def apply(self):
        k = self.key_entry.get().strip().lower()
        c = self.cmd_entry.get().strip()
        self.result = (k, c)

class ClipboardWatcher(threading.Thread):
    def __init__(self, overlay, hotkey_manager):
        super().__init__(daemon=True)
        self.overlay = overlay
        self.hotkey_manager = hotkey_manager
        self.last_text = ""
        self.pattern = re.compile(r"jemai::(?:run|exec|list)::(.+)", re.IGNORECASE)
    def run(self):
        while True:
            try:
                text = self.get_clipboard_text()
                if text != self.last_text:
                    self.last_text = text
                    match = self.pattern.search(text)
                    if match:
                        cmd = match.group(1).strip()
                        if cmd:
                            log(f"[CLIPBOARD] Detected trigger: {cmd}")
                            self.hotkey_manager.trigger_command(cmd, "CLIPBOARD")
            except Exception as e:
                log(f"[CLIPBOARD] Error: {e}")
            time.sleep(CLIPBOARD_POLL_SECONDS)
    @staticmethod
    def get_clipboard_text():
        try:
            import win32con
            win32clipboard.OpenClipboard()
            data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            return data.strip()
        except Exception:
            return ""

def create_startup_shortcut():
    try:
        import pythoncom
        from win32com.shell import shell, shellcon
        from win32com.client import Dispatch
        shell_link = Dispatch('WScript.Shell').CreateShortCut(SHORTCUT_PATH)
        shell_link.Targetpath = sys.executable
        shell_link.Arguments = os.path.abspath(__file__)
        shell_link.WorkingDirectory = os.getcwd()
        shell_link.IconLocation = sys.executable
        shell_link.save()
        log("[STARTUP] Startup shortcut created")
        return True
    except Exception as e:
        log(f"[STARTUP] Failed to create shortcut: {e}")
        return False
def remove_startup_shortcut():
    try:
        if os.path.isfile(SHORTCUT_PATH):
            os.remove(SHORTCUT_PATH)
            log("[STARTUP] Startup shortcut removed")
            return True
        return False
    except Exception as e:
        log(f"[STARTUP] Failed to remove shortcut: {e}")
        return False
def has_startup_shortcut():
    return os.path.isfile(SHORTCUT_PATH)

class JemaiTrayApp:
    def __init__(self, overlay, hotkey_mgr):
        self.overlay = overlay
        self.hotkey_mgr = hotkey_mgr
        self.icon = pystray.Icon("jemai", self.create_icon(), TRAY_TOOLTIP, menu=pystray.Menu(
            pystray.MenuItem("Enable Service", self.enable_service),
            pystray.MenuItem("Disable Service", self.disable_service),
            pystray.MenuItem("Configure Hotkeys", self.configure_hotkeys),
            pystray.MenuItem(lambda item: "Startup on Boot: ON" if has_startup_shortcut() else "Startup on Boot: OFF", self.toggle_startup),
            pystray.MenuItem("Quit", self.quit)
        ))
    def create_icon(self):
        width = 64
        height = 64
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        dc = ImageDraw.Draw(image)
        dc.rectangle((0, 0, width, height), fill='black')
        dc.text((20, 20), "J", fill='white')
        return image
    def enable_service(self):
        self.hotkey_mgr.enable()
    def disable_service(self):
        self.hotkey_mgr.disable()
    def configure_hotkeys(self):
        self.overlay.after(0, self.hotkey_mgr.open_config_gui)
    def toggle_startup(self):
        if has_startup_shortcut():
            if remove_startup_shortcut():
                log("[TRAY] Startup disabled")
        else:
            if create_startup_shortcut():
                log("[TRAY] Startup enabled")
    def quit(self):
        log("[TRAY] Quitting service")
        self.icon.stop()
        self.hotkey_mgr.stop()
        self.overlay.destroy()
        exit(0)
    def run(self):
        self.icon.run()

def heartbeat_logger():
    while True:
        log("[HEARTBEAT] JEMAI AGI Service is alive.")
        time.sleep(60)

def main():
    threading.Thread(target=launch_apps, daemon=True).start()
    threading.Thread(target=try_add_tesseract_to_path, daemon=True).start()
    overlay = JemaiOverlay()
    hotkey_mgr = HotkeyManager(overlay)
    clipboard_watcher = ClipboardWatcher(overlay, hotkey_mgr)
    clipboard_watcher.start()
    threading.Thread(target=heartbeat_logger, daemon=True).start()
    tray_app = JemaiTrayApp(overlay, hotkey_mgr)
    tray_app.run()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"[ERROR] {e}")
        try:
            from tkinter import messagebox
            messagebox.showerror("JEMAI AGI Service Error", str(e))
        except:
            pass
