import time
import serial
import pyvesc
from pyvesc import SetCurrent

PORT = "/dev/serial0"
BAUD = 115200

# Change only if your CAN IDs are different.
LEFT_CAN_ID = 0
RIGHT_CAN_ID = 1

# Start small for safety.
LEFT_CURRENT = 1.0
RIGHT_CURRENT = 1.0
RUN_TIME = 2.0

def send_current(ser, can_id, amps):
    pkt = pyvesc.encode(SetCurrent(amps, can_id=can_id))
    ser.write(pkt)
    ser.flush()

def stop_both(ser):
    send_current(ser, LEFT_CAN_ID, 0.0)
    send_current(ser, RIGHT_CAN_ID, 0.0)

def main():
    with serial.Serial(PORT, BAUD, timeout=0.1) as ser:
        time.sleep(1.0)

        try:
            print(f"Opened {PORT}")
            print(f"Sending {LEFT_CURRENT}A to CAN {LEFT_CAN_ID}")
            print(f"Sending {RIGHT_CURRENT}A to CAN {RIGHT_CAN_ID}")

            send_current(ser, LEFT_CAN_ID, LEFT_CURRENT)
            send_current(ser, RIGHT_CAN_ID, RIGHT_CURRENT)

            time.sleep(RUN_TIME)

        finally:
            print("Stopping both wheels")
            stop_both(ser)
            time.sleep(0.2)

if __name__ == "__main__":
    main()