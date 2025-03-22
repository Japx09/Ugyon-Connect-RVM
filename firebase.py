import pyrebase

config = {
  "apiKey": "AIzaSyC4OiK6mqXdFvY0QQpGpDCiolsuGJZ4f3I",
  "authDomain": "reverse-vennding-machine.firebaseapp.com",
  "databaseURL": "https://reverse-vennding-machine-default-rtdb.asia-southeast1.firebasedatabase.app",
  "storageBucket": "reverse-vennding-machine.appspot.com"
}

firebase = pyrebase.initialize_app(config)
print("Initialized")

storage = firebase.storage()
db = firebase.database()