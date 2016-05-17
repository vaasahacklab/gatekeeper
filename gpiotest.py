import RPi.GPIO as GPIO
import time

GPIO.cleanup()

# use P1 header pin numbering convention
GPIO.setmode(GPIO.BCM)

# Set up the GPIO channels - one input and one output
#GPIO.setup(11, GPIO.IN)

GPIO.setup(21, GPIO.OUT)


# Output to pin 12
GPIO.output(21, GPIO.LOW)
time.sleep(1)
GPIO.output(21, GPIO.HIGH)
time.sleep(1)
GPIO.output(21, GPIO.LOW)
time.sleep(1)
GPIO.output(21, GPIO.HIGH)
time.sleep(1)
GPIO.output(21, GPIO.LOW)
time.sleep(1)

GPIO.cleanup()
