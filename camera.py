import os
import time

display_env = os.environ.get("DISPLAY")
wayland_env = os.environ.get("WAYLAND_DISPLAY")
if display_env or wayland_env:
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

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
        self.has_display = bool(display_env or wayland_env)
        self.should_quit = False

    def _detect_tags(self):
        frame = self.cam.capture_array()
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

        tags = self.detector.detect(
            gray,
            estimate_tag_pose=True,
            camera_params=self.camera_params,
            tag_size=self.tag_size,
        )
        return frame, tags

    def _closest_tag_measurement(self, tags) -> tuple[float, float]:
        if not tags:
            return float("inf"), 0.0

        best = min(tags, key=lambda t: t.pose_t[2][0])
        return float(best.pose_t[2][0]), float(best.pose_t[0][0])

    def _direction_hint(self, distance: float, offset_x: float) -> str:
        if distance == float("inf"):
            return "NO TAG"
        if distance > 1.0:
            hint = "MOVE FORWARD"
        elif distance < 0.4:
            hint = "TOO CLOSE"
        else:
            hint = "IN RANGE"

        if abs(offset_x) > 0.1:
            hint += "  TURN " + ("LEFT" if offset_x < 0 else "RIGHT")
        return hint

    def _draw_overlay(self, frame, tags):
        for tag in tags:
            distance = float(tag.pose_t[2][0])
            offset_x = float(tag.pose_t[0][0])

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
        cv2.line(frame, (w // 2 - 20, h // 2), (w // 2 + 20, h // 2), (255, 255, 255), 1)
        cv2.line(frame, (w // 2, h // 2 - 20), (w // 2, h // 2 + 20), (255, 255, 255), 1)
        cv2.putText(frame, f"Tags: {len(tags)}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        distance, offset_x = self._closest_tag_measurement(tags)
        hint = self._direction_hint(distance, offset_x)
        color = (255, 255, 255)
        if distance != float("inf"):
            color = (0, 255, 0)
            if distance < 0.4:
                color = (0, 0, 255)
            elif abs(offset_x) > 0.1:
                color = (0, 165, 255)

        cv2.putText(frame, hint, (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    def _show_frame(self, frame):
        if not self.has_display:
            return False
        cv2.imshow("FollowBot Camera", frame)
        self.should_quit = cv2.waitKey(1) == ord('q')
        return self.should_quit

    def close(self):
        self.should_quit = True
        try:
            cv2.destroyAllWindows()
        finally:
            try:
                self.cam.stop()
            except Exception:
                pass


    def simple_stream(self):
        try:
            while True:
                frame = self.cam.capture_array()
                if self._show_frame(frame):
                    break
                if not self.has_display:
                    time.sleep(0.05)
        finally:
            self.close()


    def april_tag_stream(self):
        try:
            while True:
                frame, tags = self._detect_tags()
                self._draw_overlay(frame, tags)
                distance, offset_x = self._closest_tag_measurement(tags)

                if self._show_frame(frame):
                    break
                if not self.has_display:
                    print(
                        f"Tags: {len(tags)} | distance: "
                        f"{'inf' if distance == float('inf') else f'{distance:.2f}'} m | "
                        f"offset_x: {offset_x:.2f} m | {self._direction_hint(distance, offset_x)}"
                    )
                    time.sleep(1.0)
        finally:
            self.close()


    def get_tag_offset(self) -> tuple[float, float]:
        """
            Return tule of (distance, offset_x) to closest tag, or (inf, 0) if no tags detected
        """
        _, tags = self._detect_tags()
        return self._closest_tag_measurement(tags)


    def get_tag_offset_with_stream(self) -> tuple[float, float]:
        """
        Return tuple of (distance, offset_x) to closest tag, or (inf, 0) if no tags
        detected. Updates the preview with each tag's outline and center dot.
        """
        frame, tags = self._detect_tags()
        self._draw_overlay(frame, tags)
        self._show_frame(frame)
        return self._closest_tag_measurement(tags)

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
