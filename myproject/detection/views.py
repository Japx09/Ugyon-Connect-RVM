# detection/views.py
from django.http import JsonResponse
from django.views import View
import threading
import time
import RPi.GPIO as GPIO
import cv2
import numpy as np
import tflite_runtime.interpreter as tflite

# Global variables
is_running = False
bottle_count = 0
total_points = 0
size_label = "N/A"
detection_status = "Waiting..."
detection_thread = None

# --- GPIO and Servo Setup ---
SERVO_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)

pwm = GPIO.PWM(SERVO_PIN, 50)  # 50Hz PWM frequency
pwm.start(0)

def set_servo_angle(angle):
    duty = 2 + (angle / 18)
    pwm.ChangeDutyCycle(duty)
    time.sleep(1.0)
    pwm.ChangeDutyCycle(0)

def activate_servo():
    set_servo_angle(120)  # Move to 120 degrees
    time.sleep(1.0)
    set_servo_angle(25)   # Return to 25 degrees

# --- Camera and Model Setup ---
detect_interpreter = tflite.Interpreter(model_path="/home/japheth09/Documents/RVM_SYSTEM/rvm_env/detect.tflite")
detect_interpreter.allocate_tensors()
model_interpreter = tflite.Interpreter(model_path="/home/japheth09/Documents/RVM_SYSTEM/rvm_env/model.tflite")
model_interpreter.allocate_tensors()

detect_input_details = detect_interpreter.get_input_details()
detect_output_details = detect_interpreter.get_output_details()
model_input_details = model_interpreter.get_input_details()
model_output_details = model_interpreter.get_output_details()

with open("/home/japheth09/Documents/RVM_SYSTEM/rvm_env/labelmap.txt", 'r') as f:
    detect_labels = [line.strip() for line in f.readlines()]

detect_input_size = (detect_input_details[0]['shape'][1], detect_input_details[0]['shape'][2])

# Object detection logic
def object_detection_logic():
    global is_running, bottle_count, total_points, size_label, detection_status

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Camera not accessible")
        return

    while is_running:
        ret, frame = cap.read()
        if not ret:
            continue
        
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
                bottle_detected = True
                bottle_count += 1
                total_points += 5
                size_label = "Small"  # Adjust based on your logic
                activate_servo()  # Activate servo for detected bottle
                break  # Exit the loop after detecting one bottle

        detection_status = "Detected" if bottle_detected else "Waiting..."
        time.sleep(1)  # Control detection rate

    cap.release()
    GPIO.cleanup()  # Clean up GPIO settings when done

class StartDetectionView(View):
    def post(self, request):
        global is_running, detection_thread
        if not is_running:
            is_running = True
            detection_thread = threading.Thread(target=object_detection_logic)
            detection_thread.start()
            return JsonResponse({"status": "Detection started."})
        else:
            return JsonResponse({"status": "Detection already running."})

class StopDetectionView(View):
    def post(self, request):
        global is_running
        is_running = False
        if detection_thread:
            detection_thread.join()  # Wait for the thread to finish
        return JsonResponse({"status": "Detection stopped.", "final_data": {"bottle_count": bottle_count, "size": size_label}})

class StatusView(View):
    def get(self, request):
        return JsonResponse({"bottle_count": bottle_count, "detection_status": detection_status, "size": size_label})
