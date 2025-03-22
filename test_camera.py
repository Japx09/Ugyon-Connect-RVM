import cv2

# Function to test camera index
def test_camera_index(index):
    cap = cv2.VideoCapture(index)

    if not cap.isOpened():
        print(f"Camera at index {index} not available.")
    else:
        print(f"Camera at index {index} is available.")
        # Open a preview window to display the video stream
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame.")
                break

            cv2.imshow(f"Camera Index {index}", frame)

            # Break the loop if 'q' key is pressed
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

# Test different camera indices (0, 1, 2, etc.)
for i in range(5):  # Change the range as needed to test more indices
    test_camera_index(i)
