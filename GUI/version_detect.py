import serial
from time import sleep

# open up a serial to allow for reading in of module attachment
port = "/dev/ttyUSB0"
port2 = "/dev/ttyUSB1"
run_it = 0 # handler for starting programs

try:
    ser = serial.Serial(port, baudrate = 115200, timeout = 3)
except:
    ser = serial.Serial(port2, baudrate = 115200, timeout = 3)

sleep(2)
ser.write(b'version\n')
version = int(ser.readline().decode())
print(version)
