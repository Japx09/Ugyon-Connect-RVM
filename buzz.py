import RPi.GPIO as GPIO
import time

BUZZER_PIN = 4  # Change this to your buzzer pin

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

# Ensure buzzer is off initially
GPIO.output(BUZZER_PIN, GPIO.LOW)
print("Buzzer is off initially")

# Turn the buzzer on for 1 second, then turn it off
GPIO.output(BUZZER_PIN, GPIO.HIGH)
print("Buzzer is ON")
time.sleep(1)

GPIO.output(BUZZER_PIN, GPIO.LOW)
print("Buzzer is OFF")

GPIO.cleanup()  # Reset GPIO settings
