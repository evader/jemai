import sys
import os
import tkinter as tk
from tkinter import messagebox
import threading
import time

def flash_screen():
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.configure(bg="black")
    root.after(1000, root.destroy)  # 1 second black screen
    root.mainloop()

def write_test_file():
    fname = os.path.join(os.getcwd(), "jemai_test_file.txt")
    with open(fname, "w") as f:
        f.write("JemAI has full control!\n")
    return fname

def run_custom_script():
    script_name = "jemai_custom_script.bat"
    with open(script_name, "w") as f:
        f.write("@echo off\n")
        f.write("echo JemAI ran this script! > jemai_script_output.txt\n")
    os.system(f'start cmd /c "{script_name}"')

def show_message(msg):
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("JemAI Message", msg)
    root.destroy()

def main_ui():
    app = tk.Tk()
    app.title("JemAI Barebones Test")
    app.geometry("400x220")
    app.resizable(False, False)

    tk.Label(app, text="JemAI Barebones Kernel", font=("Segoe UI", 16, "bold")).pack(pady=10)
    tk.Button(app, text="Flash Screen", font=("Segoe UI", 12), command=lambda: threading.Thread(target=flash_screen).start()).pack(pady=8)
    tk.Button(app, text="Write File", font=("Segoe UI", 12), command=lambda: show_message(f"Wrote file: {write_test_file()}")).pack(pady=8)
    tk.Button(app, text="Run Script", font=("Segoe UI", 12), command=lambda: [run_custom_script(), show_message("Script launched!")]).pack(pady=8)
    tk.Button(app, text="Exit", font=("Segoe UI", 12), command=app.quit).pack(pady=8)

    app.mainloop()

if __name__ == "__main__":
    main_ui()
