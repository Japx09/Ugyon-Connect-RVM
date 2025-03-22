from flask import Flask, render_template, jsonify
import subprocess
import os

app = Flask(__name__)

# Correct absolute path to object_detection.py
SCRIPT_PATH = "/home/japheth09/Documents/RVM_SYSTEM/rvm_env/flask/utils/object_detection.py"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_detection', methods=['POST'])
def start_detection():
    try:
        if not os.path.exists(SCRIPT_PATH):
            return jsonify({'error': f"Script not found at {SCRIPT_PATH}"}), 500

        # Start the object detection script
        process = subprocess.Popen(['python3', SCRIPT_PATH], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        output, _ = process.communicate()

        return jsonify({'message': 'Object detection started successfully!', 'logs': output}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
