class Motors:
    def __init__(self):
        # Initialize motor control here (e.g., GPIO setup)
        pass

    def turn(self, angle):
        # Turn the robot by a certain angle (in degrees)
        # Positive angle for right turn, negative for left turn
        pass

    def move_forward(self, speed):
        # Move the robot forward at a certain speed
        # Speed should be in the range [0.0, 1.0]
        pass

    def set_speed(self, left_speed, right_speed):
        # Set the speed of the left and right motors
        # left_speed and right_speed should be in the range [-1.0, 1.0]
        # where -1.0 is full reverse, 0 is stop, and 1.0 is full forward
        pass

    def stop(self):
        # Stop both motors
        self.set_speed(0, 0)