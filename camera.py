from picamera2 import Picamera2
import cv2
from pupil_apriltags import Detector
import os
os.environ["QT_QPA_PLATFORM"] = "xcb"
os.environ["DISPLAY"] = ":0"

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


    def simple_stream(self):
        while True:
            frame = self.cam.capture_array()
            cv2.imshow("FollowBot Camera", frame)
            if cv2.waitKey(1) == ord('q'):
                break

        cv2.destroyAllWindows()


    def april_tag_stream(self):
        while True:
            frame = self.cam.capture_array()
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

            tags = self.detector.detect(
                gray,
                estimate_tag_pose=True,
                camera_params=self.camera_params,
                tag_size=self.tag_size
            )

            for tag in tags:
                # Extract pose data
                distance = tag.pose_t[2][0]
                offset_x = tag.pose_t[0][0]

                # Draw tag outline
                corners = tag.corners.astype(int)
                cv2.polylines(frame, [corners], isClosed=True,
                            color=(0, 255, 0), thickness=2)

                # Draw center dot
                center = tuple(tag.center.astype(int))
                cv2.circle(frame, center, 5, (0, 0, 255), -1)

                # Draw crosshair lines from center
                cv2.line(frame, (center[0] - 15, center[1]),
                                (center[0] + 15, center[1]), (0, 0, 255), 1)
                cv2.line(frame, (center[0], center[1] - 15),
                                (center[0], center[1] + 15), (0, 0, 255), 1)

                # Label with ID and distance
                cv2.putText(frame,
                            f"ID:{tag.tag_id}  {distance:.2f}m",
                            (corners[0][0], corners[0][1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                # Offset indicator bar at bottom of tag
                bar_center_x = center[0]
                bar_y = corners[2][1] + 15
                offset_px = int(offset_x * 100)  # scale for visibility
                cv2.line(frame, (bar_center_x, bar_y),
                                (bar_center_x + offset_px, bar_y), (255, 165, 0), 3)

            # HUD overlay
            h, w = frame.shape[:2]
            # Frame center crosshair
            cv2.line(frame, (w//2 - 20, h//2), (w//2 + 20, h//2), (255, 255, 255), 1)
            cv2.line(frame, (w//2, h//2 - 20), (w//2, h//2 + 20), (255, 255, 255), 1)

            # Tag count
            cv2.putText(frame, f"Tags: {len(tags)}", (10, 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

            # Direction hint
            if tags:
                best = min(tags, key=lambda t: t.pose_t[2][0])  # closest tag
                distance = best.pose_t[2][0]
                offset_x = best.pose_t[0][0]

                if distance > 1.0:
                    hint, color = "MOVE FORWARD", (0, 255, 0)
                elif distance < 0.4:
                    hint, color = "TOO CLOSE", (0, 0, 255)
                else:
                    hint, color = "IN RANGE", (0, 255, 0)

                if abs(offset_x) > 0.1:
                    hint += "  TURN " + ("LEFT" if offset_x < 0 else "RIGHT")
                    color = (0, 165, 255)

                cv2.putText(frame, hint, (10, h - 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            cv2.imshow("FollowBot Camera", frame)
            if cv2.waitKey(1) == ord('q'):
                break

        cv2.destroyAllWindows()


    def get_tag_offset(self) -> tuple[float, float]:
        """
            Return tule of (distance, offset_x) to closest tag, or (inf, 0) if no tags detected
        """
        frame = self.cam.capture_array()
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

        tags = self.detector.detect(
            gray,
            estimate_tag_pose=True,
            camera_params=self.camera_params,
            tag_size=self.tag_size
        )

        if not tags:
            return float('inf'), 0.0

        best = min(tags, key=lambda t: t.pose_t[2][0])  # closest tag
        distance = best.pose_t[2][0]
        offset_x = best.pose_t[0][0] # offset from center in meters (negative is left, positive is right)

        return distance, offset_x


    def get_tag_offset_with_stream(self) -> tuple[float, float]:
        """
        Return tuple of (distance, offset_x) to closest tag, or (inf, 0) if no tags
        detected. Updates the preview with each tag's outline and center dot.
        """
        frame = self.cam.capture_array()
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

        tags = self.detector.detect(
            gray,
            estimate_tag_pose=True,
            camera_params=self.camera_params,
            tag_size=self.tag_size,
        )

        for tag in tags:
            corners = tag.corners.astype(int)
            cv2.polylines(
                frame, [corners], isClosed=True, color=(0, 255, 0), thickness=2
            )
            center = tuple(tag.center.astype(int))
            cv2.circle(frame, center, 5, (0, 0, 255), -1)

        cv2.imshow("FollowBot Camera", frame)
        cv2.waitKey(1)

        if not tags:
            return float("inf"), 0.0

        best = min(tags, key=lambda t: t.pose_t[2][0])
        return float(best.pose_t[2][0]), float(best.pose_t[0][0])

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