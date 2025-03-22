import cv2
import numpy as np
import tflite_runtime.interpreter as tflite
import threading
import requests
import time
from firebase import db

# ESP32 configuration
ESP_IP = "http://192.168.123.37"  # Replace with ESP32 IP address
ESP_TRIGGER_ENDPOINT = f"{ESP_IP}/trigger"  # Endpoint to trigger ESP actions

# Load both models
detect_interpreter = tflite.Interpreter(model_path="/home/japheth09/Documents/RVM_SYSTEM/rvm_env/detect.tflite")
detect_interpreter.allocate_tensors()

model_interpreter = tflite.Interpreter(model_path="/home/japheth09/Documents/RVM_SYSTEM/rvm_env/model.tflite")
model_interpreter.allocate_tensors()

# Input and output details for both models
detect_input_details = detect_interpreter.get_input_details()
detect_output_details = detect_interpreter.get_output_details()

model_input_details = model_interpreter.get_input_details()
model_output_details = model_interpreter.get_output_details()

# Labels for detection and classification
with open("/home/japheth09/Documents/RVM_SYSTEM/rvm_env/labelmap.txt", 'r') as f:
    detect_labels = [line.strip() for line in f.readlines()]

# Labels for classification model
class_labels = ["Plastic bottle", "Empty"]

# Get input size for both models
detect_input_size = (detect_input_details[0]['shape'][1], detect_input_details[0]['shape'][2])
model_input_size = (model_input_details[0]['shape'][1], model_input_details[0]['shape'][2])

# Variables for threading and frame capture
frame = None
ret = False
stop_threads = False
frame_lock = threading.Lock()

def capture_frame(cap):
    """Continuously capture frames from the camera."""
    global frame, ret, stop_threads
    while not stop_threads:
        ret, new_frame = cap.read()
        if ret:
            with frame_lock:
                frame = cv2.rotate(new_frame, cv2.ROTATE_90_CLOCKWISE)
        else:
            print("Error: Camera not accessible or frame capture failed.")
            break

def preprocess_frame_for_detection(frame, input_size):
    """Resize and prepare frame for object detection."""
    if frame is None:
        raise ValueError("Empty frame received for preprocessing.")
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    resized_frame = cv2.resize(frame_rgb, input_size)
    return np.expand_dims(np.array(resized_frame, dtype=np.uint8), axis=0)

def send_to_esp():
    """Send a trigger request to the ESP32."""
    try:
        print(f"Sending request to ESP: {ESP_TRIGGER_ENDPOINT}")
        response = requests.get(ESP_TRIGGER_ENDPOINT, timeout=5)
        if response.status_code == 200:
            print("ESP Triggered Successfully:", response.json())
            return True
        else:
            print("ESP Trigger Failed:", response.status_code, response.text)
            return False
    except requests.exceptions.RequestException as e:
        print("Error connecting to ESP:", e)
        return False

def send_to_firebase(label):
    """Send detection data to Firebase."""
    try:
        data = {
            "status": "Plastic Detected" if label == "Plastic bottle" else "Not Plastic Bottle",
            "timestamp": time.time()
        }
        db.child("detections").push(data)
        print("Data sent to Firebase:", data)
    except Exception as e:
        print("Error sending data to Firebase:", e)

def run_object_detection():
    """Run object detection and classification on the frames."""
    global frame, ret
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Unable to access camera.")
        return

    # Wait for the camera to initialize
    time.sleep(2)

    # Start the capture thread
    capture_thread = threading.Thread(target=capture_frame, args=(cap,))
    capture_thread.start()

    try:
        while True:
            if ret:
                with frame_lock:
                    if frame is None:
                        print("No frame available yet.")
                        continue

                    # Preprocess the frame for object detection
                    input_data = preprocess_frame_for_detection(frame, detect_input_size)

                    # Run object detection model
                    detect_interpreter.set_tensor(detect_input_details[0]['index'], input_data)
                    detect_interpreter.invoke()

                    # Extract detection results
                    boxes = detect_interpreter.get_tensor(detect_output_details[0]['index'])[0]
                    classes = detect_interpreter.get_tensor(detect_output_details[1]['index'])[0]
                    scores = detect_interpreter.get_tensor(detect_output_details[2]['index'])[0]
                    num_detections = int(detect_interpreter.get_tensor(detect_output_details[3]['index'])[0])

                    print("Detection Results:")
                    print("Boxes:", boxes)
                    print("Classes:", classes)
                    print("Scores:", scores)

                    for i in range(num_detections):
                        print(f"Detection {i}: Score = {scores[i]:.2f}")
                        if scores[i] > 0.5:  # Reduced confidence threshold for debugging
                            ymin, xmin, ymax, xmax = boxes[i]
                            x = max(0, int(xmin * frame.shape[1]))
                            y = max(0, int(ymin * frame.shape[0]))
                            w = min(frame.shape[1] - x, int((xmax - xmin) * frame.shape[1]))
                            h = min(frame.shape[0] - y, int((ymax - ymin) * frame.shape[0]))

                            print(f"Bounding Box: x={x}, y={y}, w={w}, h={h}")

                            # Aspect ratio filtering (temporarily disabled for debugging)
                            aspect_ratio = h / w if w > 0 else 0
                            print(f"Aspect Ratio: {aspect_ratio}")
                            if aspect_ratio < 1.5 or aspect_ratio > 3.5:
                                print("Aspect ratio not valid for a bottle. Skipping.")
                                continue

                            # Check if detected object is a "bottle"
                            label_id = int(classes[i])
                            if label_id < len(detect_labels) and detect_labels[label_id] == "bottle":
                                print("Bottle detected.")

                                # Draw bounding box for debugging
                                

                                # Extract ROI for classification
                                bottle_roi = frame[y:y + h, x:x + w]
                                if bottle_roi.shape[0] > 0 and bottle_roi.shape[1] > 0:
                                    bottle_roi_resized = cv2.resize(bottle_roi, model_input_size)
                                    bottle_input_data = np.expand_dims(bottle_roi_resized, axis=0).astype(np.uint8)

                                    # Run classification model
                                    model_interpreter.set_tensor(model_input_details[0]['index'], bottle_input_data)
                                    model_interpreter.invoke()

                                    # Get classification results
                                    model_output_data = model_interpreter.get_tensor(model_output_details[0]['index'])[0]
                                    class_id = np.argmax(model_output_data)
                                    confidence = model_output_data[class_id]
                                    label = class_labels[class_id]

                                    # Filter out low-confidence classifications
                                    if confidence < 0.85:
                                        label = "Not Plastic Bottle"

                                    # Debug classification results
                                    print(f"Detected Object: {label}, Confidence: {confidence}")

                                    # Trigger ESP and send to Firebase
                                    current_time = time.time()
                                    if label == "Plastic bottle":
                                        print(f"Triggering ESP for {label} with confidence {confidence}")
                                        triggered = send_to_esp()
                                        if triggered:
                                            add_recent_detection(label)
                                    send_to_firebase(label)

                    # Display the frame with detection and classification
                    

            if False:  # Disable live camera display
                break

    except KeyboardInterrupt:
        print("\nProcess stopped by user.")
    finally:
        global stop_threads
        stop_threads = True
        capture_thread.join()
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    run_object_detection()
