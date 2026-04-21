import os
import subprocess
import sys
import tkinter as tk

process = None

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(PROJECT_DIR, "main.py")
PYTHON_EXECUTABLE = sys.executable

def start_camera():
    global process
    if process is None or process.poll() is not None:
        process = subprocess.Popen(
            [PYTHON_EXECUTABLE, MAIN_SCRIPT],
            cwd=PROJECT_DIR,
        )

def stop_camera():
    global process
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
        process = None

def exit_app():
    stop_camera()
    root.destroy()

root = tk.Tk()
root.title("Camera Launcher")
root.geometry("480x320")
root.configure(padx=20, pady=20)

title = tk.Label(root, text="Camera Control", font=("Arial", 22, "bold"))
title.pack(pady=20)

start_button = tk.Button(
    root,
    text="Start Camera",
    font=("Arial", 16),
    width=20,
    height=2,
    command=start_camera
)
start_button.pack(pady=10)

stop_button = tk.Button(
    root,
    text="Stop Camera",
    font=("Arial", 16),
    width=20,
    height=2,
    command=stop_camera
)
stop_button.pack(pady=10)

exit_button = tk.Button(
    root,
    text="Exit",
    font=("Arial", 16),
    width=20,
    height=2,
    command=exit_app
)
exit_button.pack(pady=10)

root.protocol("WM_DELETE_WINDOW", exit_app)
root.mainloop()
