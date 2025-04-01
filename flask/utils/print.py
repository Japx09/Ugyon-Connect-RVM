# ~/Documents/RVM_SYSTEM/rvm_env/flask/utils/print.py

import serial
import time
import sys
from datetime import datetime # Import datetime
from dateutil.relativedelta import relativedelta # Import relativedelta

# --- Configuration ---
# !!! Check and change this to your printer's serial port !!!
# Examples: '/dev/ttyAMA0', '/dev/ttyS0', '/dev/serial0'
SERIAL_PORT = '/dev/serial0' # Based on your previous sample code
BAUD_RATE = 9600 # Common baud rate, adjust if needed for your printer

# --- Helper function to safely get arguments ---
def get_argv(index, default="N/A"):
    """Gets argument from sys.argv or returns default."""
    try:
        # Arguments start from index 1 (index 0 is script name)
        return sys.argv[index]
    except IndexError:
        print(f"Warning: Argument at index {index} not provided, using default: {default}")
        return default

# --- Printer Control Functions (from your sample) ---
def reset_printer(ser):
    """Reset the printer to default settings"""
    ser.write(b"\x1B\x40")  # ESC @ (Initialize printer)
    time.sleep(0.1)

def print_text(ser, text, bold=False, underline=False, align="left"):
    """Prints text with optional bold, underline, and alignment"""
    try:
        alignments = {"left": 0, "center": 1, "right": 2}
        # Set alignment
        ser.write(b"\x1B\x61" + bytes([alignments.get(align, 0)]))
        # Set bold
        ser.write(b"\x1B\x45" + (b"\x01" if bold else b"\x00"))
        # Set underline
        ser.write(b"\x1B\x2D" + (b"\x01" if underline else b"\x00"))
        # Print text (replace errors if non-ASCII)
        ser.write(text.encode('ascii', errors='replace') + b"\n")
        time.sleep(0.1) # Allow time for buffer/printing
        # Reset styles immediately after printing the line
        ser.write(b"\x1B\x45\x00") # Bold off
        ser.write(b"\x1B\x2D\x00") # Underline off
        if align != 'left': # Reset alignment to left if it was changed
             ser.write(b"\x1B\x61\x00")

    except Exception as e:
        print(f"Error during print_text for text '{text}': {e}")


def print_qr(ser, data):
    """Prints a QR code using raw ESC/POS commands (from sample)"""
    try:
        # IMPORTANT: These ESC/POS commands for QR might be model-specific
        print(f"Attempting to print QR for data (first 30 chars): {data[:30]}...")
        # Set QR code size (example, model 2, size 8) - adjust as needed
        ser.write(b'\x1d(k\x03\x00\x31\x43\x08') # Function 167: Size
        # Set error correction level (example, M ~30%) - adjust as needed
        ser.write(b'\x1d(k\x03\x00\x31\x45\x31') # Function 169: Error Level (48=L, 49=M, 50=Q, 51=H)
        # Store data in QR code symbol storage area
        data_bytes = data.encode('ascii', errors='replace') # Encode data
        length = len(data_bytes) + 3 # Calculate length for command pL pH
        pL = length & 0xFF
        pH = (length >> 8) & 0xFF
        # Function 180: Store QR Data
        ser.write(b'\x1d(k' + bytes([pL, pH]) + b'\x31\x50\x30' + data_bytes)
        # Print the symbol data in the symbol storage area
        ser.write(b'\x1d(k\x03\x00\x31\x51\x30') # Function 181: Print QR data
        time.sleep(0.5) # Allow time for printing QR
        print("QR print commands sent.")
    except Exception as e:
        print(f"Error during print_qr: {e}")


def feed_paper(ser, lines=3):
    """Feeds paper after printing"""
    try:
        ser.write(b"\x1B\x64" + bytes([lines])) # ESC d n: Print and feed n lines
    except Exception as e:
        print(f"Error during feed_paper: {e}")

# --- Main Execution Block ---
if __name__ == "__main__":
    print(f"--- print.py starting ---")
    print(f"Received arguments: {sys.argv}") # Log all received arguments

    # --- Parse Command Line Arguments ---
    # Expected order from app.py:
    # sys.argv[0]: script name itself
    # sys.argv[1]: Transaction ID (e.g., "TXN-...")
    # sys.argv[2]: Small Count (e.g., "5")
    # sys.argv[3]: Medium Count (e.g., "2")
    # sys.argv[4]: Large Count (e.g., "1")
    # sys.argv[5]: Session Points (e.g., "10.0")
    # sys.argv[6]: iConnect ID (Placeholder, e.g., "ANON-0000")
    # sys.argv[7]: User Name (Placeholder, e.g., "Guest")
    # sys.argv[8]: QR Code Data (e.g., the Transaction ID)
    # sys.argv[9]: Timestamp String (e.g., "2025-04-02 10:30:00")

    txn_id = get_argv(1)
    small_count = get_argv(2, "0")
    medium_count = get_argv(3, "0")
    large_count = get_argv(4, "0")
    session_points = get_argv(5, "0.0")
    iconnect_id = get_argv(6, "ANON-0000") # Use default if not provided
    user_name = get_argv(7, "Guest")      # Use default if not provided
    qr_data = get_argv(8, txn_id)         # Default QR data to txn_id
    timestamp_str = get_argv(9)           # Get timestamp arg

    # --- Process Dates ---
    print_txn_time = "N/A"
    print_exp_time = "N/A"
    try:
        # Check if timestamp_str is valid before parsing
        if timestamp_str != "N/A":
             transaction_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
             expiration_time = transaction_time + relativedelta(months=1)
             print_txn_time = transaction_time.strftime('%b %d, %Y %I:%M %p') # Ex: Apr 02, 2025 12:49 AM
             print_exp_time = expiration_time.strftime('%b %d, %Y') # Ex: May 02, 2025
             print(f"Calculated Dates: Printed={print_txn_time}, Expires={print_exp_time}")
        else:
             print("Warning: Timestamp argument not provided.")
    except ValueError:
        print(f"ERROR: Invalid date format received in argument 9: '{timestamp_str}'")
    except ImportError:
        print("ERROR: python-dateutil library not found. Cannot calculate expiration.")
        # Expiration calculation requires 'pip install python-dateutil'
    except Exception as date_e:
        print(f"ERROR processing dates: {date_e}")


    # --- Initialize and Print ---
    ser = None # Initialize ser to None
    try:
        print(f"Attempting serial connection on {SERIAL_PORT} at {BAUD_RATE} baud...")
        ser = serial.Serial(SERIAL_PORT, baudrate=BAUD_RATE, timeout=1)
        print("Serial connection opened.")

        reset_printer(ser)
        print("Printer reset.")

        # --- Print Receipt Content ---
        print_text(ser, "Ugyon Connect", bold=True, align="center")
        print_text(ser, "Reverse Vending Machine", align="center")
        print_text(ser, "------------------------------", align="center")

        print_text(ser, f"iConnect ID: {iconnect_id}")
        print_text(ser, f"User: {user_name}")
        print_text(ser, f"Date Printed: {print_txn_time}") # Added Date
        print_text(ser, "------------------------------", align="center")

        print_text(ser, "Bottles This Session:")
        print_text(ser, f"  Small : {small_count}")
        print_text(ser, f"  Medium: {medium_count}")
        print_text(ser, f"  Large : {large_count}")
        print_text(ser, f"Points Earned: {session_points} points", bold=True)
        print_text(ser, "------------------------------", align="center")

        print_text(ser, f"Transaction ID: {txn_id}")
        print_text(ser, f"Expires On: {print_exp_time}") # Added Expiration
        print_text(ser, "------------------------------", align="center")

        # QR Code section
        print_text(ser, "Scan to view your account", align="center")
        print_qr(ser, qr_data)
        print_text(ser, "\n") # Add some space after QR

        # Feed paper and finish
        feed_paper(ser, 4)
        print("Printing task seems complete.")
        sys.exit(0) # Exit successfully

    except serial.SerialException as e:
        print(f"ERROR: Serial Connection Failed on {SERIAL_PORT}. Check port/permissions.")
        print(f"  Details: {e}")
        sys.exit(1) # Exit with error
    except Exception as e:
        print(f"ERROR: Unexpected error during printing sequence.")
        print(f"  Details: {e}")
        sys.exit(1) # Exit with error
    finally:
        # Ensure serial port is closed if it was opened
        if ser and ser.is_open:
            ser.close()
            print("Serial connection closed.")
        print(f"--- print.py finished ---")