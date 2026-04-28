import os
import subprocess
import threading
import time
import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageTk

import camera
from follow_controller import FollowController
from motors import Motors

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_DEVICE = "plughw:CARD=Device,DEV=0"
MUSIC_CANDIDATES = [
    os.path.join(PROJECT_DIR, "startup_music.wav"),
    os.path.join(PROJECT_DIR, "music.wav"),
    "/usr/share/sounds/alsa/Front_Center.wav",
]


def has_display() -> bool:
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


class FollowBotApp:
    def __init__(self, root):
        self.root = root
        self.camera = None
        self.motors = None
        self.controller = None
        self.music_thread = None
        self.music_process = None
        self.music_stop_event = threading.Event()
        self.running = False
        self.last_t = None
        self.feed_image = None
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.compact_layout = self.screen_width <= 1024 or self.screen_height <= 600
        self.feed_max_size = (
            (int(self.screen_width * 0.68), int(self.screen_height * 0.72))
            if self.compact_layout
            else (1100, 900)
        )

        self.root.title("FollowBot Launcher")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg="#101418")

        self.status_var = tk.StringVar(value="Ready.")
        self.detail_var = tk.StringVar(value="Press Start to launch follow mode.")

        self._build_layout()
        self._refresh_controls()
        self.root.after(33, self._tick)
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

    def _build_layout(self):
        container = tk.Frame(self.root, bg="#101418")
        container.pack(fill="both", expand=True, padx=24, pady=24)

        feed_panel = tk.Frame(container, bg="#1a222b", bd=0, highlightthickness=0)
        feed_panel.pack(side="left", fill="both", expand=True)

        self.feed_label = tk.Label(
            feed_panel,
            text="Press Start to launch FollowBot",
            font=("Arial", 20 if self.compact_layout else 24, "bold"),
            fg="#d8e1e8",
            bg="#1a222b",
            wraplength=700 if self.compact_layout else 1000,
            justify="center",
        )
        self.feed_label.pack(fill="both", expand=True, padx=24, pady=24)

        if self.compact_layout:
            side_panel = tk.Frame(container, bg="#182028", width=max(260, int(self.screen_width * 0.28)))
            side_panel.pack(side="right", fill="y", padx=(18, 0))
            side_panel.pack_propagate(False)
        else:
            side_panel = tk.Frame(container, bg="#182028", width=460)
            side_panel.pack(side="right", fill="y", padx=(24, 0))
            side_panel.pack_propagate(False)

        if self.compact_layout:
            title = tk.Label(
                side_panel,
                text="FollowBot",
                font=("Arial", 18, "bold"),
                fg="#f3f5f7",
                bg="#182028",
            )
            title.pack(pady=(18, 10))
        else:
            title = tk.Label(
                side_panel,
                text="FollowBot",
                font=("Arial", 34, "bold"),
                fg="#f3f5f7",
                bg="#182028",
            )
            title.pack(pady=(40, 20))

            subtitle = tk.Label(
                side_panel,
                text="Start opens the live camera feed and begins follow mode.",
                font=("Arial", 22),
                fg="#b7c5d3",
                bg="#182028",
                wraplength=360,
                justify="center",
            )
            subtitle.pack(pady=(0, 32))

        controls_row = tk.Frame(side_panel, bg="#182028")
        controls_row.pack(
            pady=(8 if self.compact_layout else 0, 8 if self.compact_layout else 0),
            fill="x" if self.compact_layout else "none",
        )

        self.start_button = tk.Button(
            controls_row,
            text="Start",
            font=("Arial", 20 if self.compact_layout else 28, "bold"),
            width=12 if self.compact_layout else 16,
            height=2 if self.compact_layout else 3,
            command=self.start_followbot,
        )
        self.start_button.pack(
            side="top",
            fill="x",
            padx=14 if self.compact_layout else 0,
            pady=8 if self.compact_layout else 16,
        )

        self.stop_button = tk.Button(
            controls_row,
            text="Stop",
            font=("Arial", 20 if self.compact_layout else 28, "bold"),
            width=12 if self.compact_layout else 16,
            height=2 if self.compact_layout else 3,
            command=self.stop_followbot,
        )
        self.stop_button.pack(
            side="top",
            fill="x",
            padx=14 if self.compact_layout else 0,
            pady=8 if self.compact_layout else 16,
        )

        self.exit_button = tk.Button(
            controls_row,
            text="Exit",
            font=("Arial", 20 if self.compact_layout else 28, "bold"),
            width=12 if self.compact_layout else 16,
            height=2 if self.compact_layout else 3,
            command=self.exit_app,
        )
        self.exit_button.pack(
            side="top",
            fill="x",
            padx=14 if self.compact_layout else 0,
            pady=8 if self.compact_layout else 16,
        )

        if self.compact_layout:
            status_label = tk.Label(
                side_panel,
                textvariable=self.status_var,
                font=("Arial", 13, "bold"),
                fg="#ffffff",
                bg="#182028",
                wraplength=220,
                justify="center",
            )
            status_label.pack(pady=(14, 8), padx=10)

            detail_label = tk.Label(
                side_panel,
                textvariable=self.detail_var,
                font=("Arial", 10),
                fg="#b7c5d3",
                bg="#182028",
                wraplength=220,
                justify="center",
            )
            detail_label.pack(pady=(0, 10), padx=10)
        else:
            status_label = tk.Label(
                side_panel,
                textvariable=self.status_var,
                font=("Arial", 24, "bold"),
                fg="#ffffff",
                bg="#182028",
                wraplength=360,
                justify="center",
            )
            status_label.pack(pady=(36, 16))

            detail_label = tk.Label(
                side_panel,
                textvariable=self.detail_var,
                font=("Arial", 18),
                fg="#b7c5d3",
                bg="#182028",
                wraplength=360,
                justify="center",
            )
            detail_label.pack(pady=(0, 24))

    def _refresh_controls(self):
        self.start_button.configure(state=tk.DISABLED if self.running else tk.NORMAL)
        self.stop_button.configure(state=tk.NORMAL if self.running else tk.DISABLED)

    def _music_path(self):
        for candidate in MUSIC_CANDIDATES:
            if os.path.exists(candidate):
                return candidate
        return None

    def _music_loop(self):
        music_path = self._music_path()
        if music_path is None:
            return

        while not self.music_stop_event.is_set():
            try:
                self.music_process = subprocess.Popen(
                    ["aplay", "-D", MUSIC_DEVICE, music_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                while self.music_process.poll() is None:
                    if self.music_stop_event.wait(0.1):
                        self.music_process.terminate()
                        try:
                            self.music_process.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            self.music_process.kill()
                        break
            except Exception:
                break
            finally:
                self.music_process = None

            if not self.music_stop_event.is_set():
                time.sleep(0.1)

    def _start_music(self):
        if self.music_thread is not None and self.music_thread.is_alive():
            return
        self.music_stop_event.clear()
        self.music_thread = threading.Thread(target=self._music_loop, daemon=True)
        self.music_thread.start()

    def _stop_music(self):
        self.music_stop_event.set()
        if self.music_process is not None and self.music_process.poll() is None:
            self.music_process.terminate()
            try:
                self.music_process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.music_process.kill()
        self.music_process = None

    def _ensure_camera(self):
        if self.camera is None:
            self.camera = camera.Camera()
            self.status_var.set("Camera ready.")
            self.detail_var.set(
                "Live feed started.\n"
                f"Display={self.camera.display_env!r} | Session={self.camera.session_type!r}"
            )

    def _ensure_runtime(self):
        self._ensure_camera()
        if self.motors is None:
            self.motors = Motors()
        if self.controller is None:
            self.controller = FollowController(self.motors)

    def start_followbot(self):
        if self.running:
            return
        confirmed = messagebox.askyesno(
            "Start FollowBot",
            "This will enable motor control and start follow mode. Continue?",
        )
        if not confirmed:
            return
        try:
            self._ensure_runtime()
        except Exception as exc:
            self.status_var.set("Startup failed.")
            self.detail_var.set(str(exc))
            self._shutdown_runtime()
            return
        self.running = True
        self.last_t = None
        self._start_music()
        self.status_var.set("Drive mode running.")
        music_path = self._music_path()
        if music_path is None:
            self.detail_var.set("Live camera feed is embedded in the launcher.\nAdd startup_music.wav to play music.")
        else:
            self.detail_var.set(f"Live camera feed is embedded in the launcher.\nNow playing: {os.path.basename(music_path)}")
        self._refresh_controls()

    def stop_followbot(self):
        if self.controller is not None:
            self.controller.reset()
        if self.motors is not None:
            try:
                self.motors.stop()
            except Exception:
                pass
        self._stop_music()
        self.running = False
        self.last_t = None
        self.status_var.set("Stopped.")
        self.detail_var.set("Press Start to begin drive mode.")
        self._refresh_controls()

    def _shutdown_runtime(self):
        if self.controller is not None:
            self.controller.reset()
            self.controller = None
        if self.motors is not None:
            try:
                self.motors.close()
            except Exception:
                pass
            self.motors = None
        if self.camera is not None:
            try:
                self.camera.close()
            except Exception:
                pass
            self.camera = None

    def _tick(self):
        try:
            if self.camera is not None:
                frame, distance, offset_x = self.camera.get_annotated_frame_and_measurement()
                self._update_feed(frame)
                self._update_status(distance, offset_x)

                if self.running and self.controller is not None:
                    now = time.monotonic()
                    if self.last_t is None:
                        dt = 0.05
                    else:
                        dt = max(0.001, now - self.last_t)
                    self.last_t = now
                    self.controller.step(distance, offset_x, dt)
        except Exception as exc:
            self.running = False
            self.status_var.set("Runtime error.")
            self.detail_var.set(str(exc))
            self._refresh_controls()
            self._shutdown_runtime()
        finally:
            self.root.after(33, self._tick)

    def _update_feed(self, frame):
        image = Image.fromarray(frame)
        image.thumbnail(self.feed_max_size)
        self.feed_image = ImageTk.PhotoImage(image=image)
        self.feed_label.configure(image=self.feed_image, text="")

    def _update_status(self, distance, offset_x):
        if distance == float("inf"):
            summary = "No tag detected"
        else:
            summary = f"Distance {distance:.2f} m | Offset {offset_x:.2f} m"
        if not self.running:
            summary = "Drive mode paused.\n" + summary
        self.detail_var.set(summary)

    def exit_app(self):
        self.stop_followbot()
        self._shutdown_runtime()
        self.root.destroy()


if not has_display():
    print("No graphical display detected. Run this from the Pi desktop session.")
    print("From SSH, use 'python3 main.py' for preview or 'python3 main.py --drive' to enable motors.")
    raise SystemExit(1)


root = tk.Tk()
app = FollowBotApp(root)
root.mainloop()
