#!/usr/bin/env python3
import sys
import time
import serial
import pyvesc
from pyvesc.VESC.messages import SetRPM

PORT = "/dev/ttyAMA0"
BAUD = 115200

SLAVE_CAN_ID = 88

MASTER_RPM = 3000
SLAVE_RPM = -3000   # keep negative if that makes both wheels go forward

def send_packet(ser, msg, label=""):
    pkt = pyvesc.encode(msg)
    if label:
        print(f"{label}: {pkt.hex()}")
    ser.write(pkt)
    ser.flush()

def main():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=0.1)
    except Exception as e:
        print(f"Could not open serial port: {e}")
        return 1

    try:
        print("Starting both wheels...")
        send_packet(ser, SetRPM(MASTER_RPM), "master start")
        time.sleep(0.05)
        send_packet(ser, SetRPM(SLAVE_RPM, can_id=SLAVE_CAN_ID), "slave start")
        time.sleep(3)

        print("Stopping both wheels...")
        send_packet(ser, SetRPM(0), "master stop")
        time.sleep(0.05)
        send_packet(ser, SetRPM(0, can_id=SLAVE_CAN_ID), "slave stop")
        print("Done.")
    finally:
        ser.close()

    return 0

if __name__ == "__main__":
    sys.exit(main())

