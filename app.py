from flask import Flask, jsonify, request 
from flask import url_for, redirect
from flask_cors import CORS
import json
from types import SimpleNamespace
import threading
import time
import os

lock = threading.Lock()

app = Flask(__name__, static_url_path='/static')
CORS(app)

def load_data_from_file(file_name):
    with open(file_name + ".json", "r") as f:
        return json.loads(f.read())

def save_data_to_file(file_name, data):
    with open(file_name + ".json", "w") as f:
        f.write(json.dumps(data, default=lambda o: o.__dict__, indent=4))

def save_error_log(error):
    error_data = load_data_from_file("errors")
    error_data.append({"error": error, "time": int(time.time())})
    save_data_to_file("error", error_data)

@app.route('/')
def home():
    return redirect(url_for('static', filename='index.html'))

@app.route('/getAllLogs', methods=['POST'])
def get_all_logs():
    lock.acquire()
    try:
        log_data = load_data_from_file("log")
        lock.release()
        return jsonify({"success": True, "result": log_data})
    except Exception as e:
        print(e)
        lock.release()
        save_error_log("get_all_logs")
        return jsonify({"success": False, "result": []})

@app.route('/getAllStudents', methods=['POST'])
def get_all_students():
    lock.acquire()
    try:
        std_data = load_data_from_file("std_data")
        lock.release()
        return jsonify({"success": True, "result": std_data})
    except Exception as e:
        print(e)
        lock.release()
        save_error_log("get_all_students")
        return jsonify({"success": False, "result": []})

@app.route('/addStudent', methods=['POST'])
def add_student():
    new_student_id = request.json['id']
    new_student_name = request.json['name']
    lock.acquire()
    try:
        std_data = load_data_from_file("std_data")
        std_data[str(new_student_id)] = {"Name": new_student_name, "Last_Name": "", "fingerprint_id": 0}
        save_data_to_file("std_data", std_data)
        lock.release()
        return jsonify({"success": True})
    except Exception as e:
        print(e)
        lock.release()
        save_error_log("add_student")
        return jsonify({"success": False})
    
@app.route('/removeStudent', methods=['POST'])
def remove_student():
    student_id = request.json['id']
    lock.acquire()
    try:
        std_data = load_data_from_file("std_data")
        del std_data[str(student_id)]
        save_data_to_file("std_data", std_data)
        lock.release()
        return jsonify({"success": True})
    except Exception as e:
        print(e)
        lock.release()
        save_error_log("remove_student")
        return jsonify({"success": False})
    
if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = 5001, debug = True)

