import serial
import time
from flask import Flask, jsonify, request

# Initialize serial connection
ser = serial.Serial("/dev/serial0", baudrate=9600, timeout=1)

def reset_printer():
    """Reset the printer to default settings"""
    ser.write(b"\x1B\x40")  # ESC @ (Initialize printer)
    time.sleep(0.1)

def print_text(text, bold=False, underline=False, align="left"):
    """Prints text with optional bold, underline, and alignment"""
    alignments = {"left": 0, "center": 1, "right": 2}
    ser.write(b"\x1B\x61" + bytes([alignments.get(align, 0)]))  # Align text
    ser.write(b"\x1B\x45" + (b"\x01" if bold else b"\x00"))  # Bold
    ser.write(b"\x1B\x2D" + (b"\x01" if underline else b"\x00"))  # Underline
    ser.write(text.encode('ascii') + b"\n")  # Print text
    time.sleep(0.1)
    ser.write(b"\x1B\x45\x00")  # Reset bold
    ser.write(b"\x1B\x2D\x00")  # Reset underline

def print_qr(data):
    """Prints a QR code (if supported by printer)"""
    ser.write(b"\x1D\x28\x6B\x03\x00\x31\x43\x08")  # Set QR size
    ser.write(b"\x1D\x28\x6B" + bytes([len(data) + 3, 0, 49, 80, 48]) + data.encode('ascii'))  # Store QR data
    ser.write(b"\x1D\x28\x6B\x03\x00\x31\x51\x30")  # Print QR
    time.sleep(0.5)

def feed_paper(lines=3):
    """Feeds paper after printing"""
    ser.write(b"\x1B\x64" + bytes([lines]))

# Reset printer
reset_printer()

# Imaginary iConnect Data
account_id = "ICX-984562"
user_name = "Juan Dela Cruz"
bottle_size = "Large"
points_earned = 3
total_points = 158  # Example total points after this transaction
transaction_id = "TXN-4827619"

# Print receipt
print_text("Ugyon Connect", bold=True, underline=True, align="center")
print_text("Reverse Vending Machine", align="center")
print_text("------------------------------", align="center")

# User Information
print_text(f"iConnect ID: {account_id}")
print_text(f"User: {user_name}")
print_text("------------------------------", align="center")

# Transaction Details
print_text(f"Bottle Size: {bottle_size}", bold=True)
print_text(f"Points Earned: {points_earned} points", bold=True)
print_text(f"Total Points: {total_points} points", bold=True)
print_text("------------------------------", align="center")

# Transaction ID
print_text(f"Transaction ID: {transaction_id}")
print_text("------------------------------", align="center")

# QR Code for rewards
print_text("Scan to view your account", align="center")
print_qr(f"https://ugyonconnect.com/account/{account_id}")

# Feed paper and finish
feed_paper(4)
ser.close()
