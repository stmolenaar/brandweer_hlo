# P2000 ONTVANGEN OP RASPBERRY PI 2 MET RTL-SDR
# https://nl.oneguyoneblog.com/2016/08/09/p2000-ontvangen-decoderen-raspberry-pi/
#
# vergeet niet deze regel verderop aan te passen aan je eigen RTL-SDR ontvanger (-p en -g):
# multimon_ng = subprocess.Popen("rtl_fm -f 169.65M -M fm -s 22050 -p 43
# -g 30 | multimon-ng -a FLEX -t raw -",


import argparse
import os
import re
from multiprocessing import Process, Queue
import time
import asyncio
#import RPi.GPIO as GPIO
from config import vehicle_name_lut, brandweerrooster_username, brandweerrooster_password
from brandweerrooster import incidents_websocket, OAuth2RefreshingAccessToken
from receiver import incidents_receiver

#ELAIS_UIT = 17
#RELAIS_AAN = 27

message_word_replace_lut = {
	"Brandmelding PAC": "PAC melding",
	"Handmelder OMS": "OMS",
	"Brandmelding OMS": "OMS",
	"Autom. Brand OMS": "OMS",
	"Ass. Ambu (til assistentie)": "til assistentie",
	"Ass. Ambu (afhijsen)": "Afhijsen",
	"Ass. Politie": "assistentie Politie",
	"Ass. Ambu (Afhijsen)" : "Afhijsen",
	"bv" : "B.V.",
	"Ass. Ambu" : "assistentie ambulance",
	" Li " : " links ",
	" Re " : " rechts ",
	"[Kazerne Alarm]": "",
	"Stank/Hinder. lucht (Meting) (Gev Stof: Aardgas)": "gasmeting",
	"Ongeval Binnen (koolmonoxide/co) (meting)": "C O meting",
	"Autom. Brand": "Automatische brandmelding"
}

# https://stackoverflow.com/questions/1432924/python-change-the-scripts-working-directory-to-the-scripts-own-directory
# Set working directory to script directory
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)


def alert_message_fixup(alert):
	message = alert["message"]

	# Replace keywords
	for old, new in message_word_replace_lut.items():
		message = message.replace(old, new)

	# Filter alert types (which have special alarm sounds)
	alert_type = None
#	if "reanimatie" in message.lower():
#		alert_type = "reanimatie"
	alert["alert_type"] = alert_type

	vehicles = []
	for vehicle_code, vehicle_name in vehicle_name_lut.items():
		if vehicle_code in message:
			vehicles.append(vehicle_name)
	if vehicles:
		vehicles_string = " en ".join(vehicles)
		message = f"{vehicles_string}:{message}"

	# Remove all 6 digit numerical codes starting with '12':
	message = re.sub("12[0-9]{4}([^0-9]|$)", "", message).strip()
	message = re.sub("12-[0-9]{4}([^0-9]|$)", "", message).strip()
	message = re.sub("11[0-9]{4}([^0-9]|$)", "", message).strip()
	message = re.sub("13[A-Z]{3}([^A-Z]|$)", "", message).strip()
	# Remove the gespreksgroep
	message = re.sub("BNH-[0-9]{2}([^0-9]|$)", "", message).strip()
	message = re.sub("(13GG[0-9]{2}([^0-9]|$))", "", message).strip()
	# Remove the priority of the alarm
	message = re.sub("P [0-9]{1}([^0-9]|$)", "", message).strip()
	message = re.sub("P[0-9]{1}([^0-9]|$)", "", message).strip()

	alert["message"] = message
	return alert


async def control_lights():
	print("KLIK AAN")
#	GPIO.output(RELAIS_AAN, GPIO.LOW)
#	await asyncio.sleep(0.3)
#	GPIO.output(RELAIS_AAN, GPIO.HIGH)

	await asyncio.sleep(120)

	print("KLIK UIT")
#	GPIO.output(RELAIS_UIT, GPIO.LOW)
#	await asyncio.sleep(0.3)
#	GPIO.output(RELAIS_UIT, GPIO.HIGH)


async def main():
	parser = argparse.ArgumentParser(allow_abbrev=False)
	parser.add_argument("--disable-tts", default=False, action="store_true")
	args = parser.parse_args()

	alert_queue = Queue(maxsize=128)
	if args.disable_tts:
		print("Text-to-speech disabled")
		def dummy_consumer(queue):
			while True:
				alert = queue.get()
				print(f"Ignored TTS message: {alert}")
		tts_process =dummy_consumer
	else:
		from tts import tts_process
	Process(target=tts_process, args=(alert_queue,)).start()

	alert_queue.put_nowait({
		"timestamp": "",
		"priority": None,
	   "alert_type": None,
		"message": "Het kazernealarm is begonnen"
	})

	token = OAuth2RefreshingAccessToken(
		"https://www.brandweerrooster.nl/oauth/token", "", brandweerrooster_username, brandweerrooster_password)
	async for alert in incidents_websocket(token):
	#async for alert in incidents_receiver(["000102998", "000120999"]):
		if alert is None:
			continue

		print("VOORLEZEN")
		alert = alert_message_fixup(alert)
		print(alert)

		# If the queue is full then we lose the message
		alert_queue.put_nowait(alert)

		#if time.localtime().tm_hour >= 21 or time.localtime().tm_hour < 9:
			# Turn on the lights for 2 minutes (async fire and forget)
		asyncio.create_task(control_lights())


if __name__ == "__main__":
	# Setup IO pins
#	GPIO.setmode(GPIO.BCM)
#	GPIO.setup(RELAIS_AAN, GPIO.OUT, initial=GPIO.HIGH)
#	GPIO.setup(RELAIS_UIT, GPIO.OUT, initial=GPIO.HIGH)

	asyncio.get_event_loop().run_until_complete(main())

#	GPIO.cleanup()
