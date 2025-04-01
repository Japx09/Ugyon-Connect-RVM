import cv2
import numpy as np
import tflite_runtime.interpreter as tflite
import logging
import requests
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ESP32 Configuration
ESP_IP = "http://192.168.123.41"
bottle_detected = False  # Track if a bottle has been detected

# Load labels
LABEL_PATH = "/home/japheth09/Documents/RVM_SYSTEM/rvm_env/labelmap.txt"
with open(LABEL_PATH, 'r') as f:
    detect_labels = [line.strip() for line in f.readlines()]

# Load model
MODEL_PATH = "/home/japheth09/Documents/RVM_SYSTEM/rvm_env/detect.tflite"
try:
    detect_interpreter = tflite.Interpreter(model_path=MODEL_PATH)
    detect_interpreter.allocate_tensors()
    logging.info("Model loaded successfully.")
except Exception as e:
    logging.error(f"Error loading model: {e}")
    exit()

# Get input and output tensors
input_details = detect_interpreter.get_input_details()
output_details = detect_interpreter.get_output_details()
CONFIDENCE_THRESHOLD = 0.5  

logging.info(f"Model input shape: {input_details[0]['shape']}, dtype: {input_details[0]['dtype']}")
logging.info(f"Output details: {[output['shape'] for output in output_details]}")

# Function to process image
def preprocess_image(frame):
    img = cv2.resize(frame, (input_details[0]['shape'][1], input_details[0]['shape'][2]), interpolation=cv2.INTER_AREA)
    if input_details[0]['dtype'] == np.uint8:
        img = np.expand_dims(img, axis=0).astype(np.uint8)
    else:
        img = np.expand_dims(img, axis=0).astype(np.float32) / 255.0  # Normalize for FLOAT32 models
    return img

# Capture video
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    logging.error("Webcam not accessible.")
    exit()

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        logging.warning("Failed to capture frame")
        break
   
    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    input_data = preprocess_image(frame)
   
    detect_interpreter.set_tensor(input_details[0]['index'], input_data)
    detect_interpreter.invoke()
   
    classes = detect_interpreter.get_tensor(output_details[1]['index'])[0]
    scores = detect_interpreter.get_tensor(output_details[2]['index'])[0]
   
    detected_bottle = any(detect_labels[int(classes[i])] == "bottle" and scores[i] > CONFIDENCE_THRESHOLD for i in range(len(scores)))
   
    if detected_bottle and not bottle_detected:
        logging.info("Bottle detected")
        bottle_detected = True  # Mark as detected to prevent spam

        try:
            response = requests.get(f"{ESP_IP}/trigger")
            if response.status_code == 200:
                logging.info("ESP32 successfully triggered.")
            else:
                logging.warning(f"ESP32 response code: {response.status_code}")
        except Exception as e:
            logging.error(f"Error triggering ESP32: {e}")

        time.sleep(1)  # Pause for a second after detection

    elif not detected_bottle and bottle_detected:
        logging.info("Bottle removed, ready for next detection.")
        bottle_detected = False  # Reset detection flag when no bottle is present

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()