import cv2
import numpy as np
import tflite_runtime.interpreter as tflite
import threading
import requests
import time
from firebase import db

# ESP8266 configuration
ESP_IP = "http://192.168.123.37"  # Replace with ESP8266 IP address
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
last_trigger_time = 0  # To implement a cooldown mechanism
cooldown_period = 3  # Cooldown period in seconds
min_detection_area = 5000  # Minimum bounding box area to filter small detections

recent_detections = []  # Buffer to store recent detections

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
            frame = None
            break

def preprocess_frame_for_detection(frame, input_size):
    """Resize and prepare frame for object detection."""
    if frame is None:
        raise ValueError("Empty frame received for preprocessing.")
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    resized_frame = cv2.resize(frame_rgb, input_size)
    return np.expand_dims(np.array(resized_frame, dtype=np.uint8), axis=0)

def send_to_esp():
    """Send a trigger request to the ESP8266."""
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

def is_recent_detection(label):
    """Check if the label was recently detected to prevent duplicate triggers."""
    return label in recent_detections

def add_recent_detection(label):
    """Add a label to the recent detection buffer."""
    recent_detections.append(label)
    if len(recent_detections) > 10:  # Limit buffer size
        recent_detections.pop(0)

def run_object_detection():
    """Run object detection and classification on the frames."""
    global frame, ret, last_trigger_time
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
                    try:
                        input_data = preprocess_frame_for_detection(frame, detect_input_size)
                    except ValueError as e:
                        print(f"Preprocessing error: {e}")
                        continue

                    # Run object detection model
                    detect_interpreter.set_tensor(detect_input_details[0]['index'], input_data)
                    detect_interpreter.invoke()

                    # Extract detection results
                    boxes = detect_interpreter.get_tensor(detect_output_details[0]['index'])[0]
                    classes = detect_interpreter.get_tensor(detect_output_details[1]['index'])[0]
                    scores = detect_interpreter.get_tensor(detect_output_details[2]['index'])[0]
                    num_detections = int(detect_interpreter.get_tensor(detect_output_details[3]['index'])[0])

                    print("Detection Outputs:")
                    print("Boxes:", boxes)
                    print("Classes:", classes)
                    print("Scores:", scores)

                    for i in range(num_detections):
                        if scores[i] > 0.5:  # Reduced detection confidence threshold
                            ymin, xmin, ymax, xmax = boxes[i]
                            x = max(0, int(xmin * frame.shape[1]))
                            y = max(0, int(ymin * frame.shape[0]))
                            w = max(0, int((xmax - xmin) * frame.shape[1]))
                            h = max(0, int((ymax - ymin) * frame.shape[0]))

                            # Debug bounding box and area
                            print(f"Bounding Box: x={x}, y={y}, w={w}, h={h}, Area={(xmax - xmin) * (ymax - ymin)}")

                            x_end = min(x + w, frame.shape[1])
                            y_end = min(y + h, frame.shape[0])

                            if (x_end - x) * (y_end - y) < min_detection_area:
                                continue

                            if x_end > x and y_end > y:
                                bottle_roi = frame[y:y_end, x:x_end]
                                if bottle_roi.shape[0] > 0 and bottle_roi.shape[1] > 0:
                                    bottle_roi_resized = cv2.resize(bottle_roi, model_input_size)
                                    bottle_input_data = np.expand_dims(bottle_roi_resized, axis=0).astype(np.uint8)

                                    # Debug classification input
                                    print("Bottle ROI Shape:", bottle_roi.shape)
                                    print("Resized Input Shape:", bottle_input_data.shape)

                                    # Run classification model
                                    model_interpreter.set_tensor(model_input_details[0]['index'], bottle_input_data)
                                    model_interpreter.invoke()

                                    # Get classification results
                                    model_output_data = model_interpreter.get_tensor(model_output_details[0]['index'])[0]
                                    class_id = np.argmax(model_output_data)
                                    confidence = model_output_data[class_id]
                                    label = class_labels[class_id]

                                    # Debug classification results
                                    print(f"Detected Object: {label}, Confidence: {confidence}")

                                    # Trigger ESP
                                    current_time = time.time()
                                    if label == "Plastic bottle" and confidence > 0.5:
                                        
                                        print(f"Triggering ESP for {label} with confidence {confidence}")
                                        triggered = send_to_esp()
                                        if triggered:
                                            last_trigger_time = current_time
                                            add_recent_detection(label)

                    # Display the frame with detection and classification
                    cv2.imshow('Object Detection and Classification', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
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
