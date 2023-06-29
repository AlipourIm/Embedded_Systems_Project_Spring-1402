                                                                                                                                                                                                                                                                                                                          #!/usr/bin/env python
import time
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import hashlib

key = "*^&dh18hjk@392hsfhgjhfsdfd3$#asdd$823dh3d9h3d^d03u3ehd9d2edljj#1w0"
stdid = input("Please enter stdid: ")
reader = SimpleMFRC522()
print("ready to write to RFIF, place your tag to read contents.")

try:
	id, text = reader.read()
	print("successfully read card, now please place your tag to register card")
	hasher = hashlib.sha256((key[:20] + stdid + str(id) + key[20:]).encode("UTF-8"))
	txt = f"98102024\n{hasher.hexdigest()[0:15]}"
	time.sleep(1)
	reader.write(txt)
	print("Successfully wrote to card.")
finally:
	GPIO.cleanup()
