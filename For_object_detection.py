import RPi.GPIO as GPIO
import time
import cv2
import numpy as np
import tflite_runtime.interpreter as tflite
import threading
import random
import string

# --- Servo setup ---
SERVO_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)

pwm = GPIO.PWM(SERVO_PIN, 50)  # 50Hz PWM frequency
pwm.start(0)

def set_servo_angle(angle):
    duty = 2 + (angle / 18)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.8)
    pwm.ChangeDutyCycle(0)  # Stop signal to prevent shaking

def activate_servo():
    set_servo_angle(0)  # Move to 0 degrees (trigger the servo to open)
    time.sleep(0.8)     # Wait for the servo to complete the movement

    # Only activate buzzer when servo is open
    print("Servo open, activating buzzer...")  # Debugging line
    activate_buzzer()  # Beep once when the servo is open
    time.sleep(1)      # Wait for 1 second before next beep
    activate_buzzer()  # Beep again
    time.sleep(1)
    activate_buzzer()  # One more beep if desired
    time.sleep(1)

    set_servo_angle(100)  # Return to 100 degrees (close the servo)






# --- Ultrasonic setup ---
TRIG = 23  # Trigger pin connected to GPIO23
ECHO = 24  # Echo pin connected to GPIO24

GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def measure_distance():
    GPIO.output(TRIG, False)
    time.sleep(2)

    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    pulse_start = time.time()
    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()

    pulse_end = time.time()
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150
    return distance

def categorize_distance(distance):
    if 35.0 <= distance <= 38.0:
        return "Empty", 0
    elif 10.0 <= distance <= 16.0:
        return "Large", 5
    elif 15.0 <= distance <= 29.0:
        return "Medium", 3
    elif 30.0 <= distance <= 40.0:
        return "Small", 1
    else:
        return "Empty", 0
    

# --- Buzzer setup ---
BUZZER_PIN = 4  # Use GPIO4 (pin 7) for the buzzer
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZER_PIN, GPIO.OUT)  # Set the buzzer pin as an output

# Debugging to ensure buzzer is off initially
print("Starting script...")  # Debugging line
GPIO.output(BUZZER_PIN, GPIO.LOW)  # Ensure the buzzer is off initially



def activate_buzzer(duration=0.5):
    print("Activating buzzer...")  # Debugging line
    GPIO.output(BUZZER_PIN, GPIO.HIGH)  # Turn the buzzer on
    time.sleep(duration)                # Keep it on for the duration
    GPIO.output(BUZZER_PIN, GPIO.LOW)   # Turn the buzzer off



# --- Camera setup ---
try:
    detect_interpreter = tflite.Interpreter(model_path="/home/japheth09/Documents/RVM_SYSTEM/rvm_env/detect.tflite")
    detect_interpreter.allocate_tensors()
    model_interpreter = tflite.Interpreter(model_path="/home/japheth09/Documents/RVM_SYSTEM/rvm_env/model.tflite")
    model_interpreter.allocate_tensors()
except Exception as e:
    print(f"Error loading models: {e}")
    exit()

detect_input_details = detect_interpreter.get_input_details()
detect_output_details = detect_interpreter.get_output_details()

model_input_details = model_interpreter.get_input_details()
model_output_details = model_interpreter.get_output_details()

with open("/home/japheth09/Documents/RVM_SYSTEM/rvm_env/labelmap.txt", 'r') as f:
    detect_labels = [line.strip() for line in f.readlines()]

class_labels = ["Plastic bottle", "Empty"]

detect_input_size = (detect_input_details[0]['shape'][1], detect_input_details[0]['shape'][2])
model_input_size = (model_input_details[0]['shape'][1], model_input_details[0]['shape'][2])

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Camera not accessible")
    exit()

# Lock for thread safety
lock = threading.Lock()
frame = None
ret = False

def capture_frame(cap):
    global frame, ret
    while True:
        ret, new_frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame")
            continue
        with lock:
            frame = new_frame

capture_thread = threading.Thread(target=capture_frame, args=(cap,))
capture_thread.daemon = True
capture_thread.start()

# Tracking variables
bottle_count = {"Small": 0, "Medium": 0, "Large": 0}
total_points = 0
last_detection_time = time.time()
detection_timeout = 10  # Wait 10 seconds before printing results

def generate_qr_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def print_voucher_summary():
    print("\nREVERSE VENDING MACHINE VOUCHER")
    print(f"Bottle Count-------------------------------  {sum(bottle_count.values())} Bottles")
    for size, count in bottle_count.items():
        points = count * (1 if size == 'Small' else 2 if size == 'Medium' else 3)
        print(f"{size} -----------------------------------------  {count} bottles : {points}pts")
    print(f"Total Points : {total_points}")
    print(f"QR: {generate_qr_code()}")
    
    # Prompt user for action
    while True:
        action = input("Enter [C] to Continue or Enter [S] to Stop Transaction: ").strip().upper()
        if action == 'C':
            print("Continuing the transaction...")
            return True  # Indicate to continue
        elif action == 'S':
            print("Stopping the transaction...")
            return False  # Indicate to stop

try:
    while True:
        with lock:
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                resized_frame = cv2.resize(frame_rgb, detect_input_size)
                input_data = np.expand_dims(np.array(resized_frame, dtype=np.uint8), axis=0)

                detect_interpreter.set_tensor(detect_input_details[0]['index'], input_data)
                detect_interpreter.invoke()
                boxes = detect_interpreter.get_tensor(detect_output_details[0]['index'])[0]
                classes = detect_interpreter.get_tensor(detect_output_details[1]['index'])[0]
                scores = detect_interpreter.get_tensor(detect_output_details[2]['index'])[0]
                num_detections = int(detect_interpreter.get_tensor(detect_output_details[3]['index'])[0])

                bottle_detected = False

                for i in range(num_detections):
                    if scores[i] > 0.5 and detect_labels[int(classes[i])] == "bottle":
                        x, y, w, h = boxes[i]
                        x = int(x * frame.shape[1])
                        y = int(y * frame.shape[0])
                        w = int(w * frame.shape[1])
                        h = int(h * frame.shape[0])

                        bottle_roi = frame_rgb[y:y+h, x:x+w]
                        bottle_roi_resized = cv2.resize(bottle_roi, model_input_size)
                        bottle_input_data = np.expand_dims(bottle_roi_resized, axis=0).astype(np.uint8)

                        model_interpreter.set_tensor(model_input_details[0]['index'], bottle_input_data)
                        model_interpreter.invoke()

                        model_output_data = model_interpreter.get_tensor(model_output_details[0]['index'])[0]
                        class_id = np.argmax(model_output_data)
                        label = class_labels[class_id]
                        confidence = model_output_data[class_id]

                        if label == "Plastic bottle" and confidence > 0.6:
                            print(f"Object Detected: Plastic Bottle")
                            bottle_detected = True

                            # Measure distance and categorize size
                            distance = measure_distance()
                            size_label, points = categorize_distance(distance)

                            if size_label != "Empty":
                                print(f"Size: {size_label}")
                                print(f"Points: {points}pts")
                                bottle_count[size_label] += 1
                                total_points += points
                                activate_servo()

                                # Reset last detection time for printing results
                                last_detection_time = time.time()

                # Check if no object has been detected and 10 seconds have passed
                if not bottle_detected:
                    current_time = time.time()
                    if current_time - last_detection_time >= detection_timeout:
                        continue_transaction = print_voucher_summary()
                        # Reset tracking variables after summary
                        if not continue_transaction:
                            break  # Exit the main loop if the user chooses to stop
                        bottle_count = {"Small": 0, "Medium": 0, "Large": 0}
                        total_points = 0
                        last_detection_time = current_time  # Reset the timer after printing

                # Show the frame with detection (optional)
                cv2.imshow('Object Detection and Classification', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("\nProcess stopped by user.")
finally:
    GPIO.cleanup()
    cap.release()
    cv2.destroyAllWindows()
