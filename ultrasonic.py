import RPi.GPIO as GPIO
import time

# GPIO Pins
TRIG = 23  # Trigger pin
ECHO = 24  # Echo pin

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def measure_distance():
    # Ensure the trigger pin is low
    GPIO.output(TRIG, False)
    time.sleep(0.2)  # Allow the sensor to settle

    # Send a 10 microsecond pulse to trigger
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    # Measure the duration of the pulse
    pulse_start = time.time()
    timeout = pulse_start + 0.02  # Set a timeout of 20ms for Echo pin response

    # Wait for Echo pin to go high
    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()
        if time.time() > timeout:
            raise RuntimeError("Ultrasonic sensor not responding (timeout waiting for Echo HIGH)")

    pulse_end = time.time()
    timeout = pulse_end + 0.02  # Set a timeout of 20ms for Echo pin going low

    # Wait for Echo pin to go low
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()
        if time.time() > timeout:
            raise RuntimeError("Ultrasonic sensor not responding (timeout waiting for Echo LOW)")

    # Calculate distance
    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150  # Speed of sound in cm/s divided by 2 for round trip
    return round(distance, 2)  # Round to 2 decimal places

try:
    print("Measuring distance...")
    while True:
        try:
            distance = measure_distance()
            print(f"Distance: {distance} cm")
        except RuntimeError as e:
            print(f"Error: {e}")
        time.sleep(1)  # Wait for 1 second before measuring again
except KeyboardInterrupt:
    print("Measurement stopped by user")
    GPIO.cleanup()  # Cleanup GPIO pins
