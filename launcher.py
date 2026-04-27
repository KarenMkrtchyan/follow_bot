import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(PROJECT_DIR, "main.py")
PYTHON_EXECUTABLE = sys.executable

process = None
current_mode = None


def has_display() -> bool:
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _is_running() -> bool:
    return process is not None and process.poll() is None


def _start_process(args: list[str]):
    global current_mode, process
    if _is_running():
        status_var.set("A FollowBot process is already running.")
        return

    process = subprocess.Popen(
        [PYTHON_EXECUTABLE, MAIN_SCRIPT, *args],
        cwd=PROJECT_DIR,
    )
    current_mode = "drive" if "--drive" in args else "preview"
    status_var.set(f"Running {current_mode} mode.")
    command_var.set(f"{os.path.basename(PYTHON_EXECUTABLE)} main.py {' '.join(args)}".strip())
    _refresh_controls()


def start_followbot():
    confirmed = messagebox.askyesno(
        "Start FollowBot",
        "This will enable motor control and start follow mode. Continue?",
    )
    if confirmed:
        _start_process(["--drive"])


def stop_process():
    global current_mode, process
    if not _is_running():
        status_var.set("Nothing is running.")
        process = None
        current_mode = None
        _refresh_controls()
        return

    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)

    process = None
    current_mode = None
    status_var.set("Stopped.")
    command_var.set("No active process.")
    _refresh_controls()


def exit_app():
    stop_process()
    root.destroy()


def _refresh_controls():
    running = _is_running()
    start_button.configure(state=tk.DISABLED if running else tk.NORMAL)
    stop_button.configure(state=tk.NORMAL if running else tk.DISABLED)


def _poll_process():
    global current_mode, process
    if process is not None and process.poll() is not None:
        exit_code = process.returncode
        finished_mode = current_mode or "followbot"
        process = None
        current_mode = None
        status_var.set(f"{finished_mode.capitalize()} mode exited with code {exit_code}.")
        command_var.set("No active process.")
        _refresh_controls()
    root.after(500, _poll_process)


if not has_display():
    print("No graphical display detected. Run this from the Pi desktop session.")
    print("From SSH, use 'python3 main.py' for preview or 'python3 main.py --drive' to enable motors.")
    raise SystemExit(1)


root = tk.Tk()
root.title("FollowBot Launcher")
root.geometry("520x340")
root.configure(padx=20, pady=20)

title = tk.Label(root, text="FollowBot Control", font=("Arial", 22, "bold"))
title.pack(pady=(10, 20))

subtitle = tk.Label(
    root,
    text="Press Start to launch follow mode.",
    font=("Arial", 12),
)
subtitle.pack(pady=(0, 20))

command_var = tk.StringVar(value="No active process.")
command_label = tk.Label(
    root,
    textvariable=command_var,
    font=("Arial", 10),
    wraplength=440,
    justify="center",
)
command_label.pack(pady=(0, 16))

start_button = tk.Button(
    root,
    text="Start",
    font=("Arial", 16),
    width=20,
    height=2,
    command=start_followbot,
)
start_button.pack(pady=8)

stop_button = tk.Button(
    root,
    text="Stop",
    font=("Arial", 16),
    width=20,
    height=2,
    command=stop_process,
)
stop_button.pack(pady=8)

exit_button = tk.Button(
    root,
    text="Exit",
    font=("Arial", 16),
    width=20,
    height=2,
    command=exit_app,
)
exit_button.pack(pady=8)

status_var = tk.StringVar(value="Ready.")
status_label = tk.Label(root, textvariable=status_var, font=("Arial", 12))
status_label.pack(pady=(16, 0))

_refresh_controls()
root.after(500, _poll_process)
root.protocol("WM_DELETE_WINDOW", exit_app)
root.mainloop()
