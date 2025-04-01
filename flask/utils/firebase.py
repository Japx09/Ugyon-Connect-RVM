import pyrebase # Or import pyrebase4 if you installed that

# --- IMPORTANT: Use your actual Firebase project config ---
# --- Find this in Firebase Project Settings > General > Your apps > Web app > Config ---
# --- NOTE: Pyrebase often uses the Web API Key, not a service account ---
config = {
  "apiKey": "AIzaSyCAGmw-D0ZPUkJajzooumqu0aMl1cAt6_0", # Done!
  "authDomain": "ugyonconnectapp.firebaseapp.com", # Done   !
  "databaseURL": "https://ugyonconnectapp-default-rtdb.asia-southeast1.firebasedatabase.app/", # Your DB URL
  "projectId": "ugyonconnectapp", # Done!
  "storageBucket": "ugyonconnectapp.firebasestorage.app", # Done!
  "messagingSenderId": "206650662788", # Done!
  # "serviceAccount": "/path/to/your/serviceAccountKey.json" # ALT: Auth with service account (more complex setup)
}

print("Initializing Pyrebase...")
try:
    firebase = pyrebase.initialize_app(config) # Use pyrebase4 if installed
    db = firebase.database()
    print("Pyrebase initialized.")

    # Try to write a simple test value
    print("Attempting to write test data to /pyrebase_test...")
    db.child("pyrebase_test").set({"status": "connected"})
    print("Write successful!")

    # Try to read the test value back
    print("Attempting to read test data from /pyrebase_test...")
    test_data = db.child("pyrebase_test").get().val()
    print(f"Read successful! Data: {test_data}")

    # Clean up the test data
    # print("Attempting to remove test data...")
    # db.child("pyrebase_test").remove()
    # print("Cleanup successful.")

    print("\n✅ Pyrebase seems to be working correctly!")

except Exception as e:
    print(f"\n❌ ERROR: Pyrebase failed: {e}")
    # Print detailed traceback if needed:
    # import traceback
    # traceback.print_exc()