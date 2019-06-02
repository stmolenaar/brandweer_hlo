import oauthlib.oauth2
import websockets
import ssl
import requests
import json
import threading
import time
from collections import deque

async def incidents_websocket(oauth_token):
	recent_incidents = deque(maxlen=30)

	while True:
		url = f"wss://www.brandweerrooster.nl/cable?access_token={oauth_token.get()}"

		try:
			print("Reconnecting...")
			async with websockets.connect(url, origin=url, ssl=True) as ws:
				print("Connected to websocket")
				async for message in ws:
					message = json.loads(message)

					if "type" not in message:
						if "identifier" in message and json.loads(message["identifier"])["channel"] == "IncidentNotificationsChannel":
							incident = message["message"]
							incident_id = incident["id"]
							if incident_id not in recent_incidents:
								recent_incidents.append(incident_id)

								print(incident)
								yield parse_body_brandweerrooster(incident["body"])
						else:
							print(f"Malformed message?\n{message}")
					elif message["type"] == "welcome":
						await ws.send(json.dumps({
							"command": "subscribe",
							"identifier": json.dumps({
								"channel": "IncidentNotificationsChannel"
							})
						}))
					elif message["type"] == "confirm_subscription":
						print(
							"Succesfully subscribed to the incident notifications channel.")
					elif message["type"] == "ping":
						#print(f"Received ping with timestamp {message['message']}")
						await ws.send(json.dumps({
							"type": "pong",
							"message": message["message"]
						}))
					else:
						print(f"Received message with unknown type: {message}")
		except websockets.ConnectionClosed as e:
			print(f"Connection closed: {e}")
		except Exception as e:
			print(f"Unexpected exception: {e}")


def parse_body_brandweerrooster(line):
	if not line:
		return None

	gespreksgroep = line[4:10]
	message = line

	priority = 0
	if line[:3] == "P 1" or line[:2] == "P1":
		priority = 1
	elif line[:3] == "P 2" or line[:2] == "P2":
		priority = 2
	elif line[:3] == "P 3" or line[:2] == "P3":
		priority = 3

	return {
		"timestamp": int(time.time()),
		#"capcode": capcode,
		"priority": priority,
		"message": message
	}

class OAuth2RefreshingAccessToken():
	# Authenticate using oauth2 and store the access&refresh tokens in a member
	# variable. The constructor also spawns a detached thread that requests a new
	# access token when it is about to expire.
	_authentication_url = None
	_client_id = None
	_username = None
	_password = None

	_access_token = None
	_refresh_token = None
	_expiration_time_seconds = None

	_should_stop = False
	_refresh_thread = None

	def __init__(self, authentication_url, client_id, username, password):
		self._authentication_url = authentication_url
		self._client_id = client_id
		self._username = username
		self._password = password

		# NOTE(Mathijs): blocking IO such that it can be used immediately.
		oauth_client = oauthlib.oauth2.LegacyApplicationClient(self._client_id)
		request_body = oauth_client.prepare_request_body(
			username=username, password=password)
		request_response = requests.post(url=self._authentication_url,
										 params=str.encode(request_body))

		parsed_response = oauth_client.parse_request_body_response(
			request_response.content)
		self._access_token = parsed_response["access_token"]
		self._expiration_time_seconds = parsed_response["expires_in"]
		self._refresh_token = parsed_response["refresh_token"]

		self._refresh_thread = threading.Thread(
			target=self._refresh_worker, daemon=True)
		self._refresh_thread.start()

	def _refresh_worker(self):
		print("Refresh worker started")
		print(f"OAuth2 token expires after {self._expiration_time_seconds} seconds")

		last_refresh = time.time()
		while not self._should_stop:
			time.sleep(5)

			# Refresh 20 seconds before the access token expires
			if time.time() - last_refresh < self._expiration_time_seconds - 20:
				continue
			last_refresh = time.time()

			oauth_client = oauthlib.oauth2.LegacyApplicationClient(
				self._client_id)
			request_body = request_body = oauth_client.prepare_request_body(
				username=self._username, password=self._password)
			request_body = oauth_client.prepare_refresh_body(
				request_body, refresh_token=self._refresh_token)
			request_response = requests.post(url=self._authentication_url,
											 params=str.encode(request_body))
			print(f"Initial oauth request")
			print(f"Body:     {request_body}")
			print(f"Response: {request_response.content}\n")

			parsed_response = oauth_client.parse_request_body_response(
				request_response.content)
			self._access_token = parsed_response["access_token"]
			self._expiration_time_seconds = parsed_response["expires_in"]
			self._refresh_token = parsed_response["refresh_token"]

		print("OAuth2RefreshingAccessToken worker thread stopped")

	def get(self):
		return self._access_token

	def stop_refresh(self):
		self._should_stop = True

