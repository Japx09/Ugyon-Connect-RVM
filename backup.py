import RPi.GPIO as GPIO
import time
import cv2
import numpy as np
import tflite_runtime.interpreter as tflite
import threading
from collections import deque
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rvm_system.log'),
        logging.StreamHandler()
    ]
)

class ServoController:
    def __init__(self, pin=17):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.pin, 50)  # 50Hz PWM frequency
        self.pwm.start(0)
        logging.info("Servo controller initialized")

    def set_angle(self, angle):
        """Set servo to specific angle"""
        try:
            duty = 2 + (angle / 18)
            self.pwm.ChangeDutyCycle(duty)
            time.sleep(0.5)
            self.pwm.ChangeDutyCycle(0)  # Stop signal to prevent shaking
            logging.debug(f"Servo moved to angle: {angle}")
        except Exception as e:
            logging.error(f"Error setting servo angle: {e}")

    def accept_bottle(self):
        """Sequence for accepting a bottle"""
        self.set_angle(120)  # Open flap
        time.sleep(1.0)
        self.set_angle(25)   # Close flap
        logging.info("Bottle acceptance sequence completed")

    def cleanup(self):
        """Clean up GPIO resources"""
        self.pwm.stop()
        GPIO.cleanup(self.pin)
        logging.info("Servo cleanup completed")

class UltrasonicSensor:
    def __init__(self, trigger_pin=23, echo_pin=24):
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.trigger_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)
        
        # Initialize distance thresholds
        self.size_thresholds = {
            "Large": (10.0, 16.99, 5),    # (min, max, points)
            "Medium": (17.0, 23.0, 3),
            "Small": (24.0, 30.0, 1),
            "Empty": (35.0, 38.0, 0)
        }
        logging.info("Ultrasonic sensor initialized")

    def measure_distance(self, samples=3, delay=0.1):
        """Measure distance with multiple samples for accuracy"""
        distances = []
        
        for _ in range(samples):
            try:
                GPIO.output(self.trigger_pin, False)
                time.sleep(delay)
                
                # Send trigger pulse
                GPIO.output(self.trigger_pin, True)
                time.sleep(0.00001)
                GPIO.output(self.trigger_pin, False)
                
                # Wait for echo
                pulse_start = time.time()
                timeout = pulse_start + 1.0  # 1 second timeout
                
                # Wait for echo start
                while GPIO.input(self.echo_pin) == 0:
                    pulse_start = time.time()
                    if pulse_start > timeout:
                        raise TimeoutError("Echo timeout")
                
                # Wait for echo end
                while GPIO.input(self.echo_pin) == 1:
                    pulse_end = time.time()
                    if pulse_end > timeout:
                        raise TimeoutError("Echo timeout")
                
                pulse_duration = pulse_end - pulse_start
                distance = pulse_duration * 17150  # Speed of sound conversion
                distances.append(distance)
                
            except TimeoutError as e:
                logging.warning(f"Distance measurement timeout: {e}")
                continue
            except Exception as e:
                logging.error(f"Error measuring distance: {e}")
                continue
        
        if distances:
            # Return median value to filter outliers
            return np.median(distances)
        return None

    def categorize_bottle(self, distance):
        """Categorize bottle size based on distance measurement"""
        if distance is None:
            return "Error", 0
            
        for size, (min_dist, max_dist, points) in self.size_thresholds.items():
            if min_dist <= distance <= max_dist:
                logging.info(f"Bottle categorized as {size}, Distance: {distance:.1f}cm")
                return size, points
                
        logging.warning(f"Distance {distance:.1f}cm outside of known categories")
        return "Unknown", 0

    def cleanup(self):
        """Clean up GPIO resources"""
        GPIO.cleanup([self.trigger_pin, self.echo_pin])
        logging.info("Ultrasonic sensor cleanup completed")

class RVMSystem:
    def __init__(self, camera_manager, object_detector, servo_controller, ultrasonic_sensor):
        self.camera = camera_manager
        self.detector = object_detector
        self.servo = servo_controller
        self.ultrasonic = ultrasonic_sensor
        self.total_points = 0
        self.transaction_active = False
        logging.info("RVM System initialized")

    def start_transaction(self):
        """Start a new transaction"""
        self.transaction_active = True
        self.total_points = 0
        logging.info("New transaction started")

    def end_transaction(self):
        """End current transaction"""
        self.transaction_active = False
        logging.info(f"Transaction ended. Total points: {self.total_points}")
        return self.total_points

    def process_bottle(self):
        """Process a single bottle insertion"""
        if not self.transaction_active:
            return False, "No active transaction"

        # Get frame and detect bottle
        frame = self.camera.get_stable_frame()
        if frame is None:
            return False, "No frame available"

        detections, _, _ = self.detector.detect_and_classify(frame)
        
        if not detections:
            return False, "No bottle detected"

        # Verify it's a plastic bottle with high confidence
        detection = detections[0]
        if detection['confidence'] < 0.6:
            return False, "Low confidence detection"

        # Measure distance for size classification
        distance = self.ultrasonic.measure_distance()
        if distance is None:
            return False, "Distance measurement failed"

        # Categorize bottle and get points
        size, points = self.ultrasonic.categorize_bottle(distance)
        if size == "Empty" or size == "Unknown":
            return False, f"Invalid bottle size: {size}"

        # Accept bottle and award points
        self.servo.accept_bottle()
        self.total_points += points
        
        logging.info(f"Bottle processed successfully: {size} size, {points} points awarded")
        return True, f"Processed {size} bottle for {points} points"

    def cleanup(self):
        """Clean up all components"""
        self.camera.release()
        self.servo.cleanup()
        self.ultrasonic.cleanup()
        cv2.destroyAllWindows()
        logging.info("System cleanup completed")

def main():
    try:
        # Initialize components
        camera = CameraManager()
        detector = ObjectDetector(
            detect_model_path="/path/to/detect.tflite",
            classify_model_path="/path/to/model.tflite",
            labelmap_path="/path/to/labelmap.txt"
        )
        servo = ServoController()
        ultrasonic = UltrasonicSensor()
        
        # Initialize RVM system
        rvm = RVMSystem(camera, detector, servo, ultrasonic)
        
        while True:
            if not rvm.transaction_active:
                cmd = input("Press 's' to start transaction, 'q' to quit: ").lower()
                if cmd == 'q':
                    break
                if cmd == 's':
                    rvm.start_transaction()
                    print("Transaction started. Please insert bottles.")
                continue

            # Process bottles continuously during active transaction
            success, message = rvm.process_bottle()
            print(message)
            
            if success:
                print(f"Current points: {rvm.total_points}")
            
            # Check for transaction end
            if cv2.waitKey(1) & 0xFF == ord('e'):
                points = rvm.end_transaction()
                print(f"Transaction complete. Total points: {points}")

    except KeyboardInterrupt:
        print("\nSystem shutdown initiated by user")
    finally:
        rvm.cleanup()

if __name__ == "__main__":
    main()