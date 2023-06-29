                                                                                                                                                                                                                                                                                                                          #!/usr/bin/env python
import time
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import hashlib
from picamera import PiCamera
from datetime import datetime
import I2C_LCD_driver
import threading
from signal import pthread_kill, SIGTSTP
import multiprocessing
from multiprocessing import shared_memory, Process, Manager
import os
import signal
from datetime import datetime, timedelta
import board
from digitalio import DigitalInOut, Direction
import adafruit_fingerprint
import serial
import json

if not os.path.exists("./images"):
	os.mkdir("./images")

if not os.path.exists("./std_data.json"):
	print("unable to locate data files, terminating.")
	exit()
if not os.path.exists("./log.json"):
	f = open("./log.json", "w")
	template = {"success": [], "failures": []}
	f.write(json.dumps(template))
	f.close()


reader = SimpleMFRC522()
led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

uart = serial.Serial("/dev/ttyUSB0", baudrate=57600, timeout=1)

finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)


GPIO.setmode(GPIO.BCM)

# Defining camera, lcd & RFID-reader module instances

main_lcd = I2C_LCD_driver.lcd()
camera = PiCamera()
camera.rotation = 180

###################################################

# Keypad

L1 = 26
L2 = 19
L3 = 13
L4 = 6

C1 = 5
C2 = 0
C3 = 1

GPIO.setup(L1, GPIO.OUT)
GPIO.setup(L2, GPIO.OUT)
GPIO.setup(L3, GPIO.OUT)
GPIO.setup(L4, GPIO.OUT)

GPIO.setup(C1, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(C2, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(C3, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

###################################################

# Servo Motor

GPIO.setup(17, GPIO.OUT)

servo = GPIO.PWM(17, 50)
servo.start(0)

###################################################

# Movement detection sensor

pir_pin = 23
pir_sensor = GPIO.setup(pir_pin, GPIO.IN)


###################################################
f = open("./std_data.json")
std_data = json.load(f)
f.close()
valid_std_ids = []
valid_std_id_fingerprint_ids = []
for key in std_data:
	valid_std_ids.append(key)
	if std_data[key]["fingerprint_id"] != 0:
		valid_std_id_fingerprint_ids.append(std_data[key]["fingerprint_id"])
	else:
		valid_std_id_fingerprint_ids.append(None)

f = open("./log.json")
data = json.loads(f.read())
sucessful_attemps = data["success"]
failure_attemps = data["failures"]
data = ""
f.close()


def rfid_auth(input_values):
	key = "*^&dh18hjk@392hsfhgjhfsdfd3$#asdd$823dh3d9h3d^d03u3ehd9d2edljj#1w0"
	main_lcd.lcd_display_string("Enter card/StdId", 1)
	id, text = reader.read()
	print("card read")
	data = text.split("\n")
	if len(data) == 2 and len(data[1]) >= 5:
		hasher = hashlib.sha256((key[:20] + data[0] + str(id) + key[20:]).encode("UTF-8"))
		if hasher.hexdigest()[0:len(data[1].strip())] == data[1].strip():
			input_values["status"] = 1
			input_values["auth_res"] = True
			input_values["std_num"] = data[0]
			input_values["condition"] = "rfid"
			return
	input_values["status"] = 1
	input_values["auth_res"] = False
	input_values["std_num"] = ""
	input_values["condition"] = "rfid"
	return

def readLine(line, characters):
    GPIO.output(line, GPIO.HIGH)
    pressed_key = ""
    if(GPIO.input(C1) == 1):
        pressed_key = characters[0]
    if(GPIO.input(C2) == 1):
        pressed_key = characters[1]
    if(GPIO.input(C3) == 1):
        pressed_key = characters[2]
    GPIO.output(line, GPIO.LOW)
    return pressed_key

def get_fingerprint():
	"""Get a finger print image, template it, and see if it matches!"""
	print("Waiting for finger image...")
	while finger.get_image() != adafruit_fingerprint.OK:
		pass
	print("Templating...")
	if finger.image_2_tz(1) != adafruit_fingerprint.OK:
		return False, None
	print("Searching...")
	if finger.finger_search() != adafruit_fingerprint.OK:
		return False, ""
	return True, finger.finger_id


def check_validity(std_id, counter):
	if counter < 0:
		return False, "keypad"
	elif std_id in valid_std_ids and valid_std_id_fingerprint_ids[valid_std_ids.index(std_id)] is None:
 		return True, std_id
	elif std_id in valid_std_ids and valid_std_id_fingerprint_ids[valid_std_ids.index(std_id)] is not None:
		print("Please place your finger on the fingerprint scanner.")
		valid, fingerprint_id = get_fingerprint()
		print((valid, fingerprint_id))
		if not valid and counter > 0:
			main_lcd.lcd_display_string("Try again in 2s..." + " "*16, 1)
			main_lcd.lcd_display_string(" "*16, 2)
			time.sleep(1)
			main_lcd.lcd_display_string("Try again in 1s..." + " "*16, 1)
			time.sleep(1)
			main_lcd.lcd_display_string("Try again" + " "*16, 1)
			auth_res, cond = check_validity(std_id, counter - 1)
			print(f"test {(auth_res, cond)}")
			return auth_res, cond
		elif valid_std_id_fingerprint_ids[valid_std_ids.index(std_id)] == fingerprint_id:
			return True, std_id
		else:
			return False, "keypad2"
	else:
		return False, "keypad"

def keypad_auth(input_values):
	sec = []
	while True:
		pressed_key = readLine(L1, ["1","2","3"])
		if pressed_key == "":
			pressed_key = readLine(L2, ["4","5","6"])
		if pressed_key == "":
			pressed_key = readLine(L3, ["7","8","9"])
		if pressed_key == "":
			pressed_key = readLine(L4, ["*","0","#"])
		if pressed_key == "":
			continue
		if pressed_key == "#" and len(sec) >= 8:
			std_id = "".join(sec)
			auth_res, cond = check_validity(std_id, 2)
			input_values["status"] = 1
			input_values["auth_res"] = auth_res
			input_values["std_num"] = std_id
			input_values["condition"] = "keypad"
			return
		elif pressed_key == "#":
			continue
		elif pressed_key == "*":
			sec = sec[0:-1]
			main_lcd.lcd_display_string("".join(sec)+" "*(16-len(sec)), 2)
		elif len(sec) <= 9:
			sec.append(pressed_key)
			main_lcd.lcd_display_string("".join(sec)+" "*(16-len(sec)), 2)
		time.sleep(0.3)
		if input_values["status"] == 1:
			return

def authenticator():
	status = 0
	with Manager() as manager:
		list= manager.dict({"status": 0, "auth_res": "", "std_num": "", "condition": ""})
		keypad_process = multiprocessing.Process(target=keypad_auth, args=(list, ))
		rfid_process = multiprocessing.Process(target=rfid_auth, args=(list, ))
		rfid_process.start()
		keypad_process.start()

		while True:
			if list["status"] == 1:
				if keypad_process.is_alive():
					os.kill(keypad_process.pid, signal.SIGKILL)
				if rfid_process.is_alive():
					os.kill(rfid_process.pid, signal.SIGKILL)
				return list["auth_res"], list["std_num"], list["condition"]
			time.sleep(0.5)

def display_long_str(str, str2 = ""):
	str_pad = " " * 16
	str_to_show = str_pad + str + str_pad
	str2_to_show = str_pad + str2 + str_pad
	for i in range(len(str_to_show) - 16):
		main_lcd.lcd_display_string(str_to_show[i:(i+16)], 1)
		main_lcd.lcd_display_string(str2_to_show[i:(i+16)], 2)
		time.sleep(0.005)
	main_lcd.lcd_display_string(str[0:16], 1)
	if len(str2) != 0:
		main_lcd.lcd_display_string(str2[0:16], 2)

def save_reports():
	global failure_attemps, sucessful_attemps
	with open("./log.json", "w") as f:
                data = {"success" : sucessful_attemps, "failures" : failure_attemps}
                f.write(json.dumps(data))


def generate_report(condition):
	buzz_pin = 21
	GPIO.setup(buzz_pin, GPIO.OUT)
	camera.start_preview()
	for _ in range(5):
		GPIO.output(buzz_pin, GPIO.HIGH)
		time.sleep(0.05)
		GPIO.output(buzz_pin, GPIO.LOW)
		time.sleep(0.4)
	time.sleep(1)
	report_date = datetime.now()
	camera.capture(f"./images/{report_date}.jpg")
	failure_attemps.append({"date" : f"{report_date}", "image_path" : f"./images/{report_date}.jpg", "Method" : condition})
	camera.stop_preview()
	save_reports()

def check_for_movement(time_limit = 10):
	time.sleep(0.5)
	print("Waiting for someone to pass")
	start_time = datetime.now()
	current_state = 0
	while current_state == 0 and (datetime.now() - start_time).total_seconds() <= time_limit:
		current_state = GPIO.input(pir_pin)
		time.sleep(0.01)
	if current_state == 1:
		print("someone passed")
	else:
		print("time limit exeeded.")
	return

def rotate_servo(angle):
	servo.ChangeDutyCycle(2+(angle/18))
	time.sleep(0.5)
	servo.ChangeDutyCycle(0)
	time.sleep(0.5)

def count_entries(std_id):
	count = 0
	today = datetime.today().date()
	for entry in sucessful_attemps:
		if datetime.strptime(entry["date"], "%Y-%m-%d %H:%M:%S.%f").date() == today:
			if entry["std_id"] == std_id:
				count += 1
	return  0 if count == 0 else (count//2) + 1


try:
	while True:
		print("Please place your tag on RFID reader/writer to authenticate or enter your StdId: ")
		status, std_id, condition = authenticator()
		if status == False:
			print("Auth failed, reporting.")
			lcd_thread = threading.Thread(target=display_long_str, args=("Authentication failed, Generating report...", ""))
			lcd_thread.start()
			generate_report(condition)
			lcd_thread.join()
		else:
			print(f"Welcome {std_id} to university.\nHave a great day! :D")
			main_lcd.lcd_display_string(f"StdId: {std_id}" + " "*16 , 1)
			sucessful_attemps.append({"date" : f"{datetime.now()}", "std_id" : f"{std_id}", "Method" : condition})
			main_lcd.lcd_display_string(f"Entries: {count_entries(std_id)}" + " "*16 , 2)
			save_reports()
			print("Moving barrier")
			servo.ChangeDutyCycle(7)
			rotate_servo(90)
			check_for_movement(10)
			rotate_servo(0)
		time.sleep(3)
		main_lcd.lcd_clear()
finally:
	rotate_servo(0)
	servo.stop()
	main_lcd.lcd_clear()
	GPIO.cleanup()
