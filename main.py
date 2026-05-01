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


def run_drive_mode(debug_drive=False):
    cam = camera.Camera()
    motors = Motors()
    ctrl = FollowController(motors, max_follow_distance=STOP_DISTANCE)

    last_t = time.monotonic()
    last_status = None
    last_status_time = 0.0
    last_debug_time = 0.0
    try:
        print(
            "Drive mode enabled:",
            f"stop_distance={STOP_DISTANCE:.2f}m",
            f"cruise_speed={ctrl.cruise_speed:.2f}",
            f"offset_deadband={ctrl.offset_deadband:.2f}m",
            f"max_steer_fraction={ctrl.max_steer_fraction_of_base:.2f}",
            f"max_command_step_per_second={ctrl.max_command_step_per_second:.2f}",
        )
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
            if debug_drive and now - last_debug_time >= 0.25:
                left, right = ctrl._last_command
                print(
                    "DRIVE DEBUG:",
                    f"reason={ctrl.last_reason}",
                    f"dt={dt:.3f}s",
                    f"left={left:.3f}",
                    f"right={right:.3f}",
                )
                last_debug_time = now
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
    parser.add_argument(
        "--debug-drive",
        action="store_true",
        help="Print controller stop reasons and left/right motor commands.",
    )
    args = parser.parse_args()

    if args.drive or args.debug_drive:
        run_drive_mode(debug_drive=args.debug_drive)
    else:
        print("Starting in preview-only mode. Use --drive to enable motors.")
        run_preview_mode()


if __name__ == "__main__":
    main()
