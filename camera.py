import os
os.environ["QT_QPA_PLATFORM"] = "wayland"  # lets the cv2 use the main screen

import time

import cv2
from picamera2 import Picamera2
from pupil_apriltags import Detector

class Camera:
    def __init__(self):
        self.cam = Picamera2()
        self.cam.configure(self.cam.create_preview_configuration(
            main={"size": (640, 480), "format": "RGB888"}
        ))
        self.cam.start()

        self.detector = Detector(
            families="tag36h11",  # most robust family
            nthreads=4,           
            quad_decimate=2.0,    # halves resolution before detecting for  speed boost
            quad_sigma=0.0,       # gaussian blur
            refine_edges=1,       
            decode_sharpening=0.25
        )

        # imx708 Wide corrected intrinsics at 640x480
        FOCAL_LENGTH = 409
        cx, cy = 320, 240
        self.camera_params = (FOCAL_LENGTH, FOCAL_LENGTH, cx, cy)
        self.tag_size = 0.15  # meters
        self.has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

    def _direction_hint(self, distance, offset_x):
        if distance > 1.0:
            hint = "MOVE FORWARD"
        elif distance < 0.4:
            hint = "TOO CLOSE"
        else:
            hint = "IN RANGE"

        if abs(offset_x) > 0.1:
            hint += "  TURN " + ("LEFT" if offset_x < 0 else "RIGHT")

        return hint

    def _draw_hud(self, frame, tags):
        for tag in tags:
            distance = tag.pose_t[2][0]
            offset_x = tag.pose_t[0][0]

            corners = tag.corners.astype(int)
            cv2.polylines(frame, [corners], isClosed=True, color=(0, 255, 0), thickness=2)

            center = tuple(tag.center.astype(int))
            cv2.circle(frame, center, 5, (0, 0, 255), -1)
            cv2.line(frame, (center[0] - 15, center[1]), (center[0] + 15, center[1]), (0, 0, 255), 1)
            cv2.line(frame, (center[0], center[1] - 15), (center[0], center[1] + 15), (0, 0, 255), 1)

            cv2.putText(
                frame,
                f"ID:{tag.tag_id}  {distance:.2f}m",
                (corners[0][0], corners[0][1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )

            bar_center_x = center[0]
            bar_y = corners[2][1] + 15
            offset_px = int(offset_x * 100)
            cv2.line(frame, (bar_center_x, bar_y), (bar_center_x + offset_px, bar_y), (255, 165, 0), 3)

        h, w = frame.shape[:2]
        cv2.line(frame, (w//2 - 20, h//2), (w//2 + 20, h//2), (255, 255, 255), 1)
        cv2.line(frame, (w//2, h//2 - 20), (w//2, h//2 + 20), (255, 255, 255), 1)
        cv2.putText(frame, f"Tags: {len(tags)}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        if tags:
            best = min(tags, key=lambda t: t.pose_t[2][0])
            distance = best.pose_t[2][0]
            offset_x = best.pose_t[0][0]
            hint = self._direction_hint(distance, offset_x)
            color = (0, 165, 255) if abs(offset_x) > 0.1 else (0, 255, 0)
            if distance < 0.4:
                color = (0, 0, 255)

            cv2.putText(frame, hint, (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    def _print_headless_status(self, tags):
        if not tags:
            print("Tags: 0 | no tag detected")
            return

        best = min(tags, key=lambda t: t.pose_t[2][0])
        distance = best.pose_t[2][0]
        offset_x = best.pose_t[0][0]
        hint = self._direction_hint(distance, offset_x)
        print(
            f"Tags: {len(tags)} | best ID: {best.tag_id} | "
            f"distance: {distance:.2f}m | offset_x: {offset_x:.2f}m | {hint}"
        )


    def simple_stream(self):
        try:
            while True:
                frame = self.cam.capture_array()
                if self.has_display:
                    cv2.imshow("FollowBot Camera", frame)
                    if cv2.waitKey(1) == ord('q'):
                        break
        finally:
            cv2.destroyAllWindows()
            self.cam.stop()


    def april_tag_stream(self):
        last_status_time = 0.0

        try:
            while True:
                frame = self.cam.capture_array()
                gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

                tags = self.detector.detect(
                    gray,
                    estimate_tag_pose=True,
                    camera_params=self.camera_params,
                    tag_size=self.tag_size
                )

                if self.has_display:
                    self._draw_hud(frame, tags)
                    cv2.imshow("FollowBot Camera", frame)
                    if cv2.waitKey(1) == ord('q'):
                        break
                else:
                    now = time.monotonic()
                    if now - last_status_time >= 1.0:
                        self._print_headless_status(tags)
                        last_status_time = now
        finally:
            cv2.destroyAllWindows()
            self.cam.stop()


    def print_calibration_data(self):
        self.cam.stop()
        camera_props = self.cam.camera_properties
        print(camera_props)

        # Also check the current lens position
        self.cam.configure(self.cam.create_preview_configuration())
        self.cam.start()
        metadata = self.cam.capture_metadata()
        print("Focal length:", metadata.get("FocusFoM"))
        print("Lens position:", metadata.get("LensPosition"))
