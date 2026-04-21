import time
import serial
import pyvesc
from pyvesc.VESC.messages import SetRPM


class Motors:
    def __init__(
        self,
        port="/dev/ttyAMA0",
        baud=115200,
        slave_can_id=88,
        max_rpm=3000,
        left_multiplier=1,
        right_multiplier=-1,
    ):
        """
        Assumed setup:
        - Left motor = UART-connected local VESC
        - Right motor = CAN slave VESC with CAN ID 88

        Adjust left/right multipliers if one side spins the wrong way.
        """
        self.port = port
        self.baud = baud
        self.slave_can_id = slave_can_id
        self.max_rpm = int(max_rpm)

        # Local motor on UART
        self.left_multiplier = int(left_multiplier)

        # CAN-forwarded motor
        self.right_multiplier = int(right_multiplier)

        self.ser = serial.Serial(self.port, self.baud, timeout=0.1)

    def _send(self, msg):
        packet = pyvesc.encode(msg)
        self.ser.write(packet)
        self.ser.flush()

    def _clamp(self, value, min_value=-1.0, max_value=1.0):
        return max(min_value, min(max_value, value))

    def _speed_to_rpm(self, speed):
        speed = self._clamp(speed)
        return int(speed * self.max_rpm)

    def set_speed(self, left_speed, right_speed):
        """
        left_speed and right_speed are in [-1.0, 1.0]
        """
        left_rpm = self._speed_to_rpm(left_speed) * self.left_multiplier
        right_rpm = self._speed_to_rpm(right_speed) * self.right_multiplier

        # Local VESC
        self._send(SetRPM(left_rpm))
        time.sleep(0.01)

        # CAN slave VESC
        self._send(SetRPM(right_rpm, can_id=self.slave_can_id))

    def move_forward(self, speed):
        """
        Move both wheels forward.
        speed in [0.0, 1.0]
        """
        speed = max(0.0, min(1.0, speed))
        self.set_speed(speed, speed)

    def turn(self, angle, turn_speed=0.3, duration_per_90=0.6):
        """
        Simple timed turn.
        Positive angle = right turn
        Negative angle = left turn

        You will probably need to tune:
        - turn_speed
        - duration_per_90
        """
        if angle == 0:
            return

        duration = abs(angle) / 90.0 * duration_per_90

        if angle > 0:
            # right turn: left wheel forward, right wheel backward
            self.set_speed(turn_speed, -turn_speed)
        else:
            # left turn: left wheel backward, right wheel forward
            self.set_speed(-turn_speed, turn_speed)

        time.sleep(duration)
        self.stop()

    def stop(self):
        self.set_speed(0.0, 0.0)

    def close(self):
        try:
            self.stop()
            time.sleep(0.05)
        finally:
            self.ser.close()


def main():
    motors = Motors(
        port="/dev/ttyAMA0",
        baud=115200,
        slave_can_id=88,
        max_rpm=3000,
        left_multiplier=1,
        right_multiplier=-1,
    )

    try:
        print("Forward 2 seconds")
        motors.move_forward(0.5)
        time.sleep(2)

        print("Stop")
        motors.stop()
        time.sleep(1)

        print("Right turn")
        motors.turn(90)
        time.sleep(1)

        print("Forward again")
        motors.move_forward(0.4)
        time.sleep(2)

        print("Stop")
        motors.stop()

    finally:
        motors.close()


if __name__ == "__main__":
    main()
