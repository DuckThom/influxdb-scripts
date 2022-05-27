import time
import requests
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from os import getenv

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

def login():
    global netatmo_api_token
    global netatmo_token_expiry_timestamp
    global netatmo_refresh_token

    print("Attempting login")
    loginPayload = {'client_id': NETATMO_CLIENT_ID, 'client_secret': NETATMO_CLIENT_SECRET, 'grant_type': 'password', 'username': NETATMO_USERNAME, 'password': NETATMO_PASSWORD, 'scope': 'read_station read_homecoach'}
    r = requests.post('https://api.netatmo.com/oauth2/token', data=loginPayload)

    data = r.json()
    print(data)

    now = datetime.now().timestamp()

    netatmo_api_token = data["access_token"]
    netatmo_token_expiry_timestamp = now + int(data["expires_in"]) - 600
    netatmo_refresh_token = data["refresh_token"]

    print("Login success")

def refresh():
    global netatmo_api_token
    global netatmo_token_expiry_timestamp
    global netatmo_refresh_token

    print("Refreshing token")
    refreshPayload = {'client_id': NETATMO_CLIENT_ID, 'client_secret': NETATMO_CLIENT_SECRET, 'grant_type': 'refresh_token', 'refresh_token': netatmo_refresh_token}
    r = requests.post('https://api.netatmo.com/oauth2/token', data=refreshPayload)

    data = r.json()
    print(data)

    now = datetime.now().timestamp()

    netatmo_api_token = data["access_token"]
    netatmo_token_expiry_timestamp = now + int(data["expires_in"]) - 600
    netatmo_refresh_token = data["refresh_token"]

    print("Refresh success")

if __name__ == "__main__":
    login()

    while True:
        try:
            headers = {'accept': 'application/json', 'Authorization': 'Bearer ' + netatmo_api_token}
            r = requests.get('https://api.netatmo.com/api/gethomecoachsdata', headers=headers)
        except:
            print("Failed to fetch JSON data")
            pass

        try:
            data = r.json()
            print(data)
        except:
            print("Uh oh, we didn't receive JSON, got:", r.text)
            pass

        try:
            for device in data["body"]["devices"]:
                try:
                    print("Sending data for device: " + device["station_name"])
                    now = datetime.utcnow()

                    point = Point("Temperature")\
                        .field("value", float(device["dashboard_data"]["Temperature"]))\
                        .tag("unit", "C")\
                        .tag("location", device["station_name"])\
                        .time(now, WritePrecision.NS)
                    write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)

                    point = Point("CO2")\
                        .field("value", int(device["dashboard_data"]["CO2"]))\
                        .tag("unit", "ppm")\
                        .tag("location", device["station_name"])\
                        .time(now, WritePrecision.NS)
                    write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)

                    point = Point("Humidity")\
                        .field("value", int(device["dashboard_data"]["Humidity"]))\
                        .tag("unit", "%")\
                        .tag("location", device["station_name"])\
                        .time(now, WritePrecision.NS)
                    write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)

                    point = Point("Noise")\
                        .field("value", int(device["dashboard_data"]["Noise"]))\
                        .tag("unit", "dB")\
                        .tag("location", device["station_name"])\
                        .time(now, WritePrecision.NS)
                    write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)

                    point = Point("Pressure")\
                        .field("value", float(device["dashboard_data"]["Pressure"]))\
                        .tag("unit", "mbar")\
                        .tag("location", device["station_name"])\
                        .time(now, WritePrecision.NS)
                    write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)
                except Exception as e:
                    print("Error sending air quality data", e)
        except KeyError as e:
            print("Data error", e)

        if datetime.now().timestamp() > netatmo_token_expiry_timestamp:
            refresh()

        time.sleep(60)
