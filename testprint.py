import serial

# Configure your serial connection
printer = serial.Serial(
    port='/dev/serial0',  # Update to the correct port for your device (e.g., '/dev/ttyUSB0' or '/dev/serial0' on Raspberry Pi)
    baudrate=9600,        # Update to the correct baud rate for your printer
    timeout=1
)

# Test print data
test_data = [
    "Test Print\n",
    "1234567890\n",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ\n",
    "abcdefghijklmnopqrstuvwxyz\n",
    "Special characters: !@#$%^&*()\n",
    "----------------------------\n",
    "End of Test\n"
]

# Send each line to the printer
for line in test_data:
    printer.write(line.encode('ascii'))  # Send data encoded in ASCII
