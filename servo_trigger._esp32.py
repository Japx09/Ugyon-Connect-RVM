import requests

# ESP8266 details
ESP8266_IP = "192.168.123.49"  # Replace with your ESP8266's IP address
ESP8266_PORT = 80  # Port number for the ESP8266 server

def send_command():
    """Send a GET request to the ESP8266 to trigger the servo."""
    try:
        url = f"http://{ESP8266_IP}:{ESP8266_PORT}/ROTATE"
        response = requests.get(url, timeout=10)  # Send a GET request
        if response.status_code == 200:
            print("Command sent successfully! Response:", response.text)
        else:
            print(f"Failed to send command. HTTP status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Type 's' to rotate the servo or 'q' to quit.")
    while True:
        try:
            user_input = input("Enter your command: ").strip().lower()
            if user_input == "s":
                send_command()  # Call the ESP8266 link
            elif user_input == "q":
                print("Exiting...")
                break
            else:
                print("Invalid input. Please type 's' to send the command or 'q' to quit.")
        except KeyboardInterrupt:
            print("\nExiting...")
            break
