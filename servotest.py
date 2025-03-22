import RPi.GPIO as GPIO
import time

# Set up the GPIO mode
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Define the servo pin
servo_pin = 17

# Set up the servo pin as output
GPIO.setup(servo_pin, GPIO.OUT)

# Create a PWM instance on the servo pin with a frequency of 50Hz (standard for servos)
pwm = GPIO.PWM(servo_pin, 50)

# Start PWM with a duty cycle of 0 (servo off)
pwm.start(0)

# Function to set the servo angle
def set_servo_angle(angle):
    duty = 2 + (angle / 18)  # Convert angle to duty cycle (2 to 12)
    pwm.ChangeDutyCycle(duty)

# Move from 0 to 180 degrees and back to 0 in 1 second
try:
    # Move to 0 degrees (0.5 seconds)
    set_servo_angle(0)
    time.sleep(0.5)

    # Move back to 100 degrees (0.5 seconds)
    set_servo_angle(100)
    time.sleep(0.5)

finally:
    # Clean up the GPIO setup
    pwm.stop()
    GPIO.cleanup()
