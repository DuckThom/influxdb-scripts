import socket
import time
import uuid
from datetime import datetime
from os import getenv

from io import BytesIO
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from urllib.parse import parse_qs, urlparse

load_dotenv()

INFLUXDB_TOKEN = getenv("INFLUXDB_TOKEN")
INFLUXDB_ENDPOINT = getenv("INFLUXDB_ENDPOINT")
INFLUXDB_ORG = getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = getenv("INFLUXDB_BUCKET")

NETATMO_CLIENT_ID = getenv("NETATMO_CLIENT_ID")
NETATMO_CLIENT_SECRET = getenv("NETATMO_CLIENT_SECRET")
NETATMO_USERNAME = getenv("NETATMO_USERNAME")
NETATMO_PASSWORD = getenv("NETATMO_PASSWORD")

client = InfluxDBClient(url=INFLUXDB_ENDPOINT, token=INFLUXDB_TOKEN)
write_api = client.write_api(write_options=SYNCHRONOUS)

state = {
    'netatmo_generated_code': '',
    'netatmo_api_token': '',
    'netatmo_token_expiry_timestamp': 0.0,
    'netatmo_refresh_token': ''
}


class WebServer(BaseHTTPRequestHandler):
    def do_GET(self):
        global state

        incoming_query = parse_qs(urlparse(self.path).query)

        # incoming_query.get("state").pop()
        state['netatmo_generated_code'] = incoming_query.get("code").pop()

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Ok, you may now close this browser tab")

        # self.server.shutdown()


# Save the auth token state to a file to load again on startup
def save_state():
    import json

    global state

    # Serializing json
    json_state = json.dumps(state, indent=4)

    # Writing to sample.json
    with open("state.json", "w") as outfile:
        outfile.write(json_state)

        print("Saved auth state to file")


# Load the auth token state from
def load_state():
    import json

    global state

    try:
        with open("state.json", "r") as openfile:
            json_state = json.load(openfile)
        state = json_state

        print("Loaded auth state from file")
    except:
        pass


# Request new token data from the API
def update_token(payload):
    global state

    refresh_request = requests.post('https://api.netatmo.com/oauth2/token', data=payload)

    update_token_data = refresh_request.json()
    print(update_token_data)

    state['netatmo_api_token'] = update_token_data["access_token"]
    state['netatmo_token_expiry_timestamp'] = datetime.now().timestamp() + int(update_token_data["expires_in"]) - 600
    state['netatmo_refresh_token'] = update_token_data["refresh_token"]

    save_state()


# Build a fetch token payload
def fetch_token():
    global state

    print("Fetching token")
    login_payload = {
        'grant_type': 'authorization_code',
        'scope': 'read_station read_homecoach',
        'redirect_uri': 'http://localhost:5567/',  # Mandatory, but doesn't do anything
        'client_id': NETATMO_CLIENT_ID,
        'client_secret': NETATMO_CLIENT_SECRET,
        'code': state['netatmo_generated_code'],
    }

    update_token(login_payload)
    print("Login success")


# Build a refresh token payload
def refresh():
    global state

    print("Refreshing token")
    refresh_payload = {
        'grant_type': 'refresh_token',
        'client_id': NETATMO_CLIENT_ID,
        'client_secret': NETATMO_CLIENT_SECRET,
        'refresh_token': state['netatmo_refresh_token'],
    }

    update_token(refresh_payload)
    print("Refresh success")


# Open an HTTP server to listen for an authorization response
def listen_for_code():
    httpd = HTTPServer(server_address=("127.0.0.1", 5567), RequestHandlerClass=WebServer)
    httpd.handle_request()


# Push data to InfluxDB
def push_data():
    try:
        headers = {'accept': 'application/json', 'Authorization': 'Bearer ' + state['netatmo_api_token']}
        r = requests.get('https://api.netatmo.com/api/gethomecoachsdata', headers=headers)
    except:
        print("Failed to fetch JSON data")
        pass

    try:
        data = r.json()
        # print(data)
    except:
        print("Uh oh, we didn't receive JSON, got:", r.text)
        pass

    try:
        for device in data["body"]["devices"]:
            try:
                print("Sending data for device: " + device["station_name"])
                now = datetime.utcnow()

                point = Point("Temperature") \
                    .field("value", float(device["dashboard_data"]["Temperature"])) \
                    .tag("unit", "C") \
                    .tag("location", device["station_name"]) \
                    .time(now, WritePrecision.NS)
                write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)

                point = Point("CO2") \
                    .field("value", int(device["dashboard_data"]["CO2"])) \
                    .tag("unit", "ppm") \
                    .tag("location", device["station_name"]) \
                    .time(now, WritePrecision.NS)
                write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)

                point = Point("Humidity") \
                    .field("value", int(device["dashboard_data"]["Humidity"])) \
                    .tag("unit", "%") \
                    .tag("location", device["station_name"]) \
                    .time(now, WritePrecision.NS)
                write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)

                point = Point("Noise") \
                    .field("value", int(device["dashboard_data"]["Noise"])) \
                    .tag("unit", "dB") \
                    .tag("location", device["station_name"]) \
                    .time(now, WritePrecision.NS)
                write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)

                point = Point("Pressure") \
                    .field("value", float(device["dashboard_data"]["Pressure"])) \
                    .tag("unit", "mbar") \
                    .tag("location", device["station_name"]) \
                    .time(now, WritePrecision.NS)
                write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)
            except Exception as e:
                print("Error sending air quality data", e)
    except KeyError as e:
        print("Data error", e)


if __name__ == "__main__":
    load_state()

    """
    https://api.netatmo.com/oauth2/authorize?
        client_id=[YOUR_APP_ID]
        &redirect_uri=[YOUR_REDIRECT_URI]
        &scope=[SCOPE_SPACE_SEPARATED]
        &state=[SOME_ARBITRARY_BUT_UNIQUE_STRING]
    """

    if not state['netatmo_generated_code']:
        url = "https://api.netatmo.com/oauth2/authorize?client_id=" + NETATMO_CLIENT_ID + "&redirect_uri=http://localhost:5567/&scope=read_station%20read_homecoach"

        print("Open the following URL in your browser to receive an access token")
        print("")
        print(url)

        listen_for_code()

        if not state['netatmo_generated_code']:
            print("[Error] Did not receive a code")
            exit(1)

    if not state['netatmo_token_expiry_timestamp']:
        fetch_token()
    elif state['netatmo_token_expiry_timestamp'] != 0.0 and datetime.now().timestamp() > state['netatmo_token_expiry_timestamp']:
        refresh()

    while True:
        sleep_time = 5

        if state['netatmo_api_token']:
            push_data()
            sleep_time = 60

        if state['netatmo_token_expiry_timestamp'] != 0.0 and datetime.now().timestamp() > state['netatmo_token_expiry_timestamp']:
            refresh()

        time.sleep(sleep_time)

