import RPi.GPIO as GPIO

# get the PCB version with the ID number
Pin0 = 7
Pin1 = 7
Pin2 = 7

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(Pin0, GPIO.IN)
GPIO.setup(Pin1, GPIO.IN)
GPIO.setup(Pin2, GPIO.IN)


ID = 3 + GPIO.input(Pin0) + GPIO.input(Pin1)*2 + GPIO.input(Pin2)*4
print(ID)
