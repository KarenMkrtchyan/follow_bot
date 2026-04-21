import time
import camera
from motors import Motors

STOP_DISTANCE = 2.0
OFFSET_DEADBAND = 0.1
FORWARD_SPEED = 0.5
TURN_ANGLE = 10


def main():
    cam = camera.Camera()
    drive = Motors()

    try:
        while True:
            dist, offset_x = cam.get_tag_offset()
            print(f"Distance: {dist:.2f} m, Offset X: {offset_x:.2f} m")

            if dist > STOP_DISTANCE:
                print("TOO FAR AWAY")
                drive.stop()

            else:
                if offset_x > OFFSET_DEADBAND:
                    print("TURNING RIGHT")
                    drive.turn(TURN_ANGLE)
                elif offset_x < -OFFSET_DEADBAND:
                    print("TURNING LEFT")
                    drive.turn(-TURN_ANGLE)
                else:
                    print("STRAIGHT")
                    drive.move_forward(FORWARD_SPEED)

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("Stopping robot...")

    finally:
        drive.stop()
        drive.close()


if __name__ == "__main__":
    main()
