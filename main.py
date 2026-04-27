import argparse
import time

import camera
from follow_controller import FollowController
from motors import Motors

STOP_DISTANCE = 2.0


def _fmt_dist(dist: float) -> str:
    if dist == float("inf"):
        return "inf"
    return f"{dist:.2f}"


def _status_summary(dist: float, offset_x: float) -> str:
    parts = [f"Distance: {_fmt_dist(dist)} m", f"Offset X: {offset_x:.2f} m"]
    if dist == float("inf"):
        parts.append("NO TAG")
    elif dist > STOP_DISTANCE:
        parts.append("TOO FAR AWAY")
    else:
        parts.append("IN RANGE")
    return " | ".join(parts)


def run_preview_mode():
    cam = camera.Camera()
    try:
        print(
            "Display detection:",
            f"has_display={cam.has_display},",
            f"DISPLAY={cam.display_env!r},",
            f"WAYLAND_DISPLAY={cam.wayland_env!r},",
            f"XDG_SESSION_TYPE={cam.session_type!r}",
        )
        while True:
            dist, offset_x = cam.get_tag_offset_with_stream()
            if cam.should_quit:
                break
    except KeyboardInterrupt:
        print("Stopping preview...")
    finally:
        cam.close()


def run_drive_mode():
    cam = camera.Camera()
    motors = Motors()
    ctrl = FollowController(motors, max_follow_distance=STOP_DISTANCE)

    last_t = time.monotonic()
    last_status = None
    last_status_time = 0.0
    try:
        print(
            "Display detection:",
            f"has_display={cam.has_display},",
            f"DISPLAY={cam.display_env!r},",
            f"WAYLAND_DISPLAY={cam.wayland_env!r},",
            f"XDG_SESSION_TYPE={cam.session_type!r}",
        )
        while True:
            now = time.monotonic()
            dt = now - last_t
            last_t = now

            dist, offset_x = cam.get_tag_offset_with_stream()
            if cam.should_quit:
                break
            status = _status_summary(dist, offset_x)
            if status != last_status or now - last_status_time >= 1.0:
                print(status)
                last_status = status
                last_status_time = now
            ctrl.step(dist, offset_x, dt)
    except KeyboardInterrupt:
        print("Stopping robot...")
    finally:
        try:
            ctrl.reset()
            motors.stop()
        finally:
            motors.close()
            cam.close()


def main():
    parser = argparse.ArgumentParser(description="FollowBot AprilTag runtime")
    parser.add_argument(
        "--drive",
        action="store_true",
        help="Enable motor control and follow the detected AprilTag.",
    )
    args = parser.parse_args()

    if args.drive:
        run_drive_mode()
    else:
        print("Starting in preview-only mode. Use --drive to enable motors.")
        run_preview_mode()


if __name__ == "__main__":
    main()
