# ========== Imports ==========
from flask import Flask, render_template, jsonify, redirect, url_for
import subprocess
import os
import logging
import pyrebase # Or pyrebase4 if that's what you installed
from datetime import datetime
import sys
import traceback # Import traceback for more detailed error printing

# ========== Pyrebase Initialization ==========
try:
    # --- IMPORTANT: Use your actual Firebase project config ---
    config = {
      "apiKey": "AIzaSyCAGmw-D0ZPUkJajzooumqu0aMl1cAt6_0",
      "authDomain": "ugyonconnectapp.firebaseapp.com",
      "databaseURL": "https://ugyonconnectapp-default-rtdb.asia-southeast1.firebasedatabase.app",
      "projectId": "ugyonconnectapp",
      "storageBucket": "ugyonconnectapp.firebasestorage.app", # Corrected key name
      "messagingSenderId": "206650662788",
      "appId": "1:206650662788:web:a64aafad56954fc70c07d1",
      "measurementId": "G-KNTRT62Q59" # Optional for Pyrebase, but included
    }
    firebase_pyrebase = pyrebase.initialize_app(config) # Use pyrebase4 if needed
    db = firebase_pyrebase.database()
    transaction_ref_pyrebase = db.child("current_transaction")
    print("✅ Pyrebase Initialized Successfully.")

except Exception as e:
    print(f"****************************************************")
    print(f"ERROR: Failed to initialize Pyrebase: {e}")
    print(f"Ensure config details are correct.")
    print(f"Database reset/clear functionality might not work.")
    print(f"****************************************************")
    transaction_ref_pyrebase = None

# ========== Flask App Setup ==========
app = Flask(__name__)

# --- Path to scripts using ABSOLUTE paths ---
# --- Make sure these paths are exactly correct for your system ---
SCRIPT_PATH = (
    "/home/japheth09/Documents/RVM_SYSTEM/rvm_env/flask/utils/object_detection.py"
)
PRINT_SCRIPT_PATH = (
    "/home/japheth09/Documents/RVM_SYSTEM/rvm_env/flask/utils/print.py"
)

process = None # Global variable to hold the subprocess

# ========== Helper Function ==========
def _stop_object_detection_process():
    """Stops the background object detection process if running."""
    global process
    print("[STOP_HELPER] Attempting to stop detection process...")
    print(f"[STOP_HELPER] Current process object: {process}")
    if process and process.poll() is None:
        pid = process.pid
        print(f"[STOP_HELPER] Process object found (PID: {pid}), polling state: {process.poll()}")
        try:
            print(f"[STOP_HELPER] Attempting process.terminate() on PID: {pid}")
            process.terminate()
            process.wait(timeout=2)
            print(f"[STOP_HELPER] Process terminate successful (or already ended) for PID: {pid}.")
            process = None
            return True
        except subprocess.TimeoutExpired:
            print(f"[STOP_HELPER] Process terminate timed out for PID: {pid}. Attempting kill.")
            try:
                 process.kill()
                 process.wait()
                 print(f"[STOP_HELPER] Process kill successful for PID: {pid}.")
            except Exception as kill_e:
                 print(f"[STOP_HELPER] Error during process.kill() for PID: {pid}: {kill_e}")
            finally:
                 process = None
            return True
        except Exception as e:
            print(f"[STOP_HELPER] Error during process.terminate()/wait() for PID: {pid}: {e}")
            process = None
            return False
    elif process:
         print(f"[STOP_HELPER] Process object exists but poll state is not None (State: {process.poll()}). Assuming stopped.")
         process = None
         return True
    else:
        print("[STOP_HELPER] Process object is None. Nothing to stop.")
        return True

# ========== Routes ==========

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/select_option")
def select_option():
    return render_template("select_option.html")


@app.route("/qr_code")
def qr_code():
    return render_template("qr_code.html")


@app.route("/transaction")
def transaction():
    return render_template("transaction.html")


@app.route("/thank_you")
def thank_you():
    return render_template("thank_you.html")


@app.route("/anonymous_transaction")
def anonymous_transaction():
    global process
    print("[ANON_TXN] Accessing /anonymous_transaction route...")

    # --- Initialize/Reset Firebase Transaction Data using Pyrebase ---
    print("[ANON_TXN] Attempting to reset Firebase data...")
    if transaction_ref_pyrebase:
        try:
            reset_data = { 'small': 0, 'medium': 0, 'large': 0, 'points': 0.0 }
            transaction_ref_pyrebase.set(reset_data)
            print("[ANON_TXN] Firebase data reset successful via Pyrebase.")
        except Exception as fb_error:
             print(f"[ANON_TXN] ERROR: Failed to initialize Firebase data via Pyrebase: {fb_error}")
             # traceback.print_exc()
    else:
        print("[ANON_TXN] WARNING: Pyrebase not initialized. Cannot reset transaction data.")

    # --- Start Object Detection Subprocess ---
    print("[ANON_TXN] Attempting to start object detection script...")
    try:
        if not os.path.exists(SCRIPT_PATH):
            print(f"[ANON_TXN] Error: Script not found at {SCRIPT_PATH}")
            return jsonify({'error': f"Script not found at {SCRIPT_PATH}"}), 500

        if process and process.poll() is None:
             print("[ANON_TXN] Warning: Detection process seems to be already running. Stopping first.")
             _stop_object_detection_process()

        print(f"[ANON_TXN] Starting script: {SCRIPT_PATH}")
        python_executable = sys.executable
        process = subprocess.Popen(
            [python_executable, SCRIPT_PATH],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        print(f"[ANON_TXN] Script process started with PID: {process.pid} using {python_executable}")
        return render_template("anonymous_transaction.html")

    except Exception as e:
        print(f"[ANON_TXN] ERROR starting subprocess or rendering template: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Server error starting transaction: {str(e)}'}), 500

# --- Updated /finish_transaction route ---
@app.route("/finish_transaction")
def finish_transaction():
    print("\n" + "="*20 + " /finish_transaction START " + "="*20)

    # --- Fetch data from Firebase ---
    final_data = None
    print("[FINISH_TXN] Checking Pyrebase reference...")
    if transaction_ref_pyrebase:
        try:
            print("[FINISH_TXN] Attempting to fetch data from Firebase path: /current_transaction")
            fb_data_raw = transaction_ref_pyrebase.get()
            print(f"[FINISH_TXN] Raw data object from Pyrebase: {fb_data_raw}")
            final_data = fb_data_raw.val()
            print(f"[FINISH_TXN] Data value type: {type(final_data)}")
            if final_data:
                print(f"[FINISH_TXN] Successfully fetched data: {final_data}")
            else:
                 print("[FINISH_TXN] WARNING: No data found (or empty node) at /current_transaction in Firebase.")
                 final_data = {'small': 0, 'medium': 0, 'large': 0, 'points': 0.0}
        except Exception as fb_error:
            print(f"[FINISH_TXN] ERROR: Could not fetch data from Firebase: {fb_error}")
            traceback.print_exc()
            final_data = {'small': 0, 'medium': 0, 'large': 0, 'points': 0.0}
    else:
        print("[FINISH_TXN] WARNING: Pyrebase not initialized. Using default data.")
        final_data = {'small': 0, 'medium': 0, 'large': 0, 'points': 0.0}

    # --- Prepare data for print script ---
    print("[FINISH_TXN] Preparing data for print script...")
    try:
        small_count = str(final_data.get('small', 0) if final_data else 0)
        medium_count = str(final_data.get('medium', 0) if final_data else 0)
        large_count = str(final_data.get('large', 0) if final_data else 0)
        session_points = "{:.1f}".format(float(final_data.get('points', 0.0) if final_data else 0.0))
        txn_id = f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        iconnect_id = "ANON-0000"
        user_name = "Guest"
        qr_data = txn_id
        current_timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[FINISH_TXN] Data prepared: TxnID={txn_id}, S={small_count}, M={medium_count}, L={large_count}, Pts={session_points}, Time={current_timestamp_str}")

    except Exception as data_prep_e:
        print(f"[FINISH_TXN] ERROR preparing data for print script: {data_prep_e}")
        traceback.print_exc()
        small_count, medium_count, large_count, session_points = '0','0','0','0.0'
        txn_id = f"TXN-ERR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        iconnect_id = "ANON-ERR"
        user_name = "Error"
        qr_data = txn_id
        current_timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # --- Attempt to print ---
    print("[FINISH_TXN] Checking print script path...")
    print_success = False
    if not os.path.exists(PRINT_SCRIPT_PATH):
         print(f"[FINISH_TXN] ERROR: Print script not found at {PRINT_SCRIPT_PATH}")
    else:
        try:
            python_executable = sys.executable
            args_to_pass = [
                python_executable, PRINT_SCRIPT_PATH, txn_id, small_count,
                medium_count, large_count, session_points, iconnect_id,
                user_name, qr_data,
                current_timestamp_str # Argument 9
            ]
            print(f"[FINISH_TXN] Running print script: {args_to_pass}")

            print_process = subprocess.run(
                args_to_pass, capture_output=True, text=True, check=False, timeout=30
            )
            print(f"[FINISH_TXN] Print script finished with return code: {print_process.returncode}")
            if print_process.returncode == 0:
                print("[FINISH_TXN] Print script execution SUCCESSFUL.")
                if print_process.stdout: print(f"[FINISH_TXN] Print script stdout:\n{print_process.stdout}")
                print_success = True
            else:
                print(f"[FINISH_TXN] ERROR: Print script execution FAILED.")
                if print_process.stderr: print(f"[FINISH_TXN] Print script stderr:\n{print_process.stderr}")
                if print_process.stdout: print(f"[FINISH_TXN] Print script stdout (error case):\n{print_process.stdout}")

        except subprocess.TimeoutExpired:
             print(f"[FINISH_TXN] ERROR: Print script timed out.")
        except Exception as e:
            print(f"[FINISH_TXN] ERROR: Failed to run print script: {e}")
            traceback.print_exc()

    # --- Stop Object Detection (calls helper) ---
    print("[FINISH_TXN] Proceeding to stop object detection...")
    stop_success = _stop_object_detection_process()
    print(f"[FINISH_TXN] Stop detection helper returned: {stop_success}")

    # --- Data Clearing is REMOVED from here ---

    # --- Redirect to Thank You page ---
    print("[FINISH_TXN] Redirecting to /thank_you...")
    print("="*20 + " /finish_transaction END " + "="*20 + "\n")
    return redirect(url_for('thank_you'))

# --- Removed clear logic from here ---
@app.route("/stop_detection")
def stop_detection():
    """Directly stops detection, bypassing print. Data clear moved."""
    print("\n" + "="*20 + " /stop_detection START " + "="*20)
    stop_success = _stop_object_detection_process()
    print(f"[STOP_DETECT] Stop detection helper returned: {stop_success}")
    print("[STOP_DETECT] Redirecting to /thank_you...")
    print("="*20 + " /stop_detection END " + "="*20 + "\n")
    return redirect(url_for('thank_you'))

# --- ADDED THIS NEW ROUTE ---
@app.route("/clear_session", methods=['POST'])
def clear_session():
    """Clears the /current_transaction node in Firebase."""
    print("\n" + "="*20 + " /clear_session START " + "="*20)
    if transaction_ref_pyrebase:
        try:
            print("[CLEAR_SESSION] Attempting to clear Firebase data...")
            transaction_ref_pyrebase.set({}) # or remove()
            print("[CLEAR_SESSION] Firebase data cleared successfully.")
            return jsonify({'status': 'success', 'message': 'Session data cleared.'})
        except Exception as fb_error:
            print(f"[CLEAR_SESSION] ERROR clearing Firebase data: {fb_error}")
            # traceback.print_exc()
            return jsonify({'status': 'error', 'message': str(fb_error)}), 500
    else:
        print("[CLEAR_SESSION] WARNING: Pyrebase not initialized. Cannot clear data.")
        return jsonify({'status': 'error', 'message': 'Pyrebase service not available'}), 500
# --- END OF NEW ROUTE ---

# ========== Main Execution ==========
if __name__ == "__main__":
    print("Starting Flask application...")
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)