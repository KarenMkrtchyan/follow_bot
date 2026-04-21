import camera
from motors import Motors

STOP_DISTANCE = 2

def main():
    cam = camera.Camera()
    motors = Motors()
    # cam.april_tag_stream()

    while True:
        dist, offset_x = cam.get_tag_offset_with_stream()
        print(f"Distance: {dist:.2f} m, Offset X: {offset_x:.2f} m")
        if dist > STOP_DISTANCE:
            print("TOO FAR AWAY")
            motors.stop()
        else:
            print("IN RANGE")
            motors.move_forward(0.5)
        if offset_x > 0.1:
            print("TURNING RIGHT")
            motors.turn(10)
        elif offset_x < -0.1:
            print("TURNING LEFT")
            motors.turn(-10)
        else:
            print("STRAIGHT")
            # motors.move_forward(0.5)

if __name__ == "__main__":
    main()