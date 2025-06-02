import RPi.GPIO as GPIO
import time

RED = 17
YELLOW = 27
GREEN = 22

GPIO.setmode(GPIO.BCM)
GPIO.setup(RED, GPIO.OUT)
GPIO.setup(YELLOW, GPIO.OUT)
GPIO.setup(GREEN, GPIO.OUT)

try:
    while True:
        GPIO.output(RED, GPIO.LOW)      # เปิดไฟแดง
        GPIO.output(YELLOW, GPIO.HIGH)
        GPIO.output(GREEN, GPIO.HIGH)
        time.sleep(1)

        GPIO.output(RED, GPIO.HIGH)
        GPIO.output(YELLOW, GPIO.LOW)   # เปิดไฟเหลือง
        GPIO.output(GREEN, GPIO.HIGH)
        time.sleep(1)

        GPIO.output(RED, GPIO.HIGH)
        GPIO.output(YELLOW, GPIO.HIGH)
        GPIO.output(GREEN, GPIO.LOW)    # เปิดไฟเขียว
        time.sleep(1)

except KeyboardInterrupt:
    GPIO.cleanup()
