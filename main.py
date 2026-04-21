import time

import camera
from follow_controller import FollowController
from motors import Motors

STOP_DISTANCE = 2.0


def _fmt_dist(dist: float) -> str:
    if dist == float("inf"):
        return "inf"
    return f"{dist:.2f}"


def main():
    cam = camera.Camera()
    motors = Motors()
    ctrl = FollowController(motors, max_follow_distance=STOP_DISTANCE)

    last_t = time.monotonic()
    while True:
        now = time.monotonic()
        dt = now - last_t
        last_t = now

        dist, offset_x = cam.get_tag_offset_with_stream()
        print(f"Distance: {_fmt_dist(dist)} m, Offset X: {offset_x:.2f} m")

        if dist == float("inf"):
            print("NO TAG")
        elif dist > STOP_DISTANCE:
            print("TOO FAR AWAY")
        else:
            print("IN RANGE")

        ctrl.step(dist, offset_x, dt)


if __name__ == "__main__":
    main()
