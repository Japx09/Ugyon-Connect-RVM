import cv2
import numpy as np
import tflite_runtime.interpreter as tflite
import threading
import time

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

frame = None
ret = False
running = True
process_frame_interval = 3  # Process every 3rd frame
frame_count = 0

# Function to continuously capture frames
def capture_frame(cap):
    global frame, ret, running
    while running:
        ret, temp_frame = cap.read()
        if ret:
            frame = temp_frame

# Optimized bounding box drawing
def draw_bounding_box(image, x, y, w, h, label, confidence):
    thickness = max(1, int(min(w, h) / 50))
    color = (0, 255, 0) if confidence > 0.75 else (0, 255, 255) if confidence > 0.5 else (0, 0, 255)
    cv2.rectangle(image, (x, y), (x + w, y + h), color, thickness)
    cv2.putText(image, f"{label}: {confidence:.2f}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, thickness)

# Function to process frames
def process_frame():
    global frame, running, frame_count
    while running:
        if not ret:
            continue
        frame_count += 1
        if frame_count % process_frame_interval != 0:
            continue

        temp_frame = frame.copy()

        # Preprocess the frame for object detection
        frame_rgb = cv2.cvtColor(temp_frame, cv2.COLOR_BGR2RGB)
        resized_frame = cv2.resize(frame_rgb, detect_input_size, interpolation=cv2.INTER_NEAREST)
        input_data = np.expand_dims(np.array(resized_frame, dtype=np.uint8), axis=0)

        # Run object detection model
        detect_interpreter.set_tensor(detect_input_details[0]['index'], input_data)
        detect_interpreter.invoke()

        # Extract detection results
        boxes = detect_interpreter.get_tensor(detect_output_details[0]['index'])[0]
        classes = detect_interpreter.get_tensor(detect_output_details[1]['index'])[0]
        scores = detect_interpreter.get_tensor(detect_output_details[2]['index'])[0]
        num_detections = int(detect_interpreter.get_tensor(detect_output_details[3]['index'])[0])

        for i in range(num_detections):
            if scores[i] > 0.5 and detect_labels[int(classes[i])] == "bottle":
                ymin, xmin, ymax, xmax = boxes[i]
                x = int(xmin * temp_frame.shape[1])
                y = int(ymin * temp_frame.shape[0])
                w = int((xmax - xmin) * temp_frame.shape[1])
                h = int((ymax - ymin) * temp_frame.shape[0])

                # Extract the ROI for the bottle
                bottle_roi = frame_rgb[y:y + h, x:x + w]
                if bottle_roi.size == 0:
                    continue
                bottle_roi_resized = cv2.resize(bottle_roi, model_input_size, interpolation=cv2.INTER_NEAREST)
                bottle_input_data = np.expand_dims(bottle_roi_resized, axis=0).astype(np.uint8)

                # Run the classification model
                model_interpreter.set_tensor(model_input_details[0]['index'], bottle_input_data)
                model_interpreter.invoke()

                # Get classification results
                model_output_data = model_interpreter.get_tensor(model_output_details[0]['index'])[0]
                class_id = np.argmax(model_output_data)
                confidence = model_output_data[class_id]
                label = class_labels[class_id]

                # Draw bounding box and label
                draw_bounding_box(temp_frame, x, y, w, h, label, confidence)

        # Display the video with detections and classification
        fps = 1 / (time.time() - start_time)
        cv2.putText(temp_frame, f"FPS: {fps:.2f}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.imshow('Object Detection and Classification', temp_frame)

        # Quit the program
        if cv2.waitKey(1) & 0xFF == ord('q'):
            running = False
            break

# Start capturing video
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

capture_thread = threading.Thread(target=capture_frame, args=(cap,))
capture_thread.daemon = True
capture_thread.start()

process_frame_thread = threading.Thread(target=process_frame)
process_frame_thread.start()

capture_thread.join()
process_frame_thread.join()

# Release video capture and close windows
cap.release()
cv2.destroyAllWindows()
