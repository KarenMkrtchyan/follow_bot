import os
import time
import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageTk

import camera
from follow_controller import FollowController
from motors import Motors


def has_display() -> bool:
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


class FollowBotApp:
    def __init__(self, root):
        self.root = root
        self.camera = None
        self.motors = None
        self.controller = None
        self.running = False
        self.last_t = None
        self.feed_image = None

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
            font=("Arial", 24, "bold"),
            fg="#d8e1e8",
            bg="#1a222b",
        )
        self.feed_label.pack(fill="both", expand=True, padx=24, pady=24)

        side_panel = tk.Frame(container, bg="#182028", width=460)
        side_panel.pack(side="right", fill="y", padx=(24, 0))
        side_panel.pack_propagate(False)

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

        self.start_button = tk.Button(
            side_panel,
            text="Start",
            font=("Arial", 28, "bold"),
            width=16,
            height=3,
            command=self.start_followbot,
        )
        self.start_button.pack(pady=16)

        self.stop_button = tk.Button(
            side_panel,
            text="Stop",
            font=("Arial", 28, "bold"),
            width=16,
            height=3,
            command=self.stop_followbot,
        )
        self.stop_button.pack(pady=16)

        self.exit_button = tk.Button(
            side_panel,
            text="Exit",
            font=("Arial", 28, "bold"),
            width=16,
            height=3,
            command=self.exit_app,
        )
        self.exit_button.pack(pady=16)

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
        self.status_var.set("Drive mode running.")
        self.detail_var.set("Live camera feed is embedded in the launcher.")
        self._refresh_controls()

    def stop_followbot(self):
        if self.controller is not None:
            self.controller.reset()
        if self.motors is not None:
            try:
                self.motors.stop()
            except Exception:
                pass
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
        image.thumbnail((1100, 900))
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
