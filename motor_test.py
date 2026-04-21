import serial
import pyvesc
from pyvesc.VESC.messages import GetValues, SetDutyCycle
import time

PORT = '/dev/ttyAMA0'
ser = serial.Serial(PORT, 115200, timeout=0.05)

def get_measurements():
    ser.reset_input_buffer()
    ser.write(pyvesc.encode_request(GetValues))
    time.sleep(0.1)
    buf = ser.read(ser.in_waiting or 64)
    msg, _ = pyvesc.decode(buf)
    return msg

def set_duty(duty):
    ser.write(pyvesc.encode(SetDutyCycle(duty)))

# telemetry check
m = get_measurements()
if m:
    print(f"RPM:           {m.rpm}")
    print(f"Voltage:       {m.v_in}")
    print(f"Motor current: {m.avg_motor_current}")
    print(f"Input current: {m.avg_input_current}")
    print(f"Duty cycle:    {m.duty_cycle_now}")
    print(f"FET temp:      {m.temp_fet}")
    print(f"Motor temp:    {m.temp_motor}")
    print(f"Fault code:    {m.mc_fault_code}")
else:
    print("No response from VESC")

# spin forward 1 second
print("\nForward...")
for _ in range(20):
    set_duty(0.4)
    time.sleep(0.05)

set_duty(0)
time.sleep(1)

# spin reverse 1 second
print("Reverse...")
for _ in range(20):
    set_duty(-0.4)
    time.sleep(0.05)

set_duty(0)
print("Done.")
ser.close()
