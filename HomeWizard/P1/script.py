import time
import requests
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from os import getenv
from dotenv import load_dotenv
from decimal import *

load_dotenv()

INFLUXDB_TOKEN = getenv("INFLUXDB_TOKEN")
INFLUXDB_ENDPOINT = getenv("INFLUXDB_ENDPOINT")
INFLUXDB_ORG = getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = getenv("INFLUXDB_BUCKET")

HOMEWIZARD_P1_ENDPOINT = getenv("HOMEWIZARD_P1_ENDPOINT")

client = InfluxDBClient(url=INFLUXDB_ENDPOINT, token=INFLUXDB_TOKEN)
write_api = client.write_api(write_options=SYNCHRONOUS)

getcontext().prec = 3

if __name__ == "__main__":
    while True:
        try:
            r = requests.get(HOMEWIZARD_P1_ENDPOINT)
        except:
            print("Failed to fetch JSON data")
            pass

        print(r.text)

        try:
            data = r.json()
        except:
            print("Uh oh, we didn't receive JSON, got:", r.text)
            pass

        now = datetime.utcnow()

        try:
            point = Point("active_power_w")\
                .field("value", int(data["active_power_w"]))\
                .tag("unit", "W")\
                .time(now, WritePrecision.NS)
            write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)

            point = Point("active_power_l1_w")\
                .field("value", int(data["active_power_l1_w"]))\
                .tag("unit", "W")\
                .time(now, WritePrecision.NS)
            write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)
            
            point = Point("active_power_l2_w")\
                .field("value", int(data["active_power_l2_w"]))\
                .tag("unit", "W")\
                .time(now, WritePrecision.NS)
            write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)
            
            point = Point("active_power_l3_w")\
                .field("value", int(data["active_power_l3_w"]))\
                .tag("unit", "W")\
                .time(now, WritePrecision.NS)
            write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)
            
            point = Point("total_power_import_t1")\
                .field("value", Decimal(data["total_power_import_t1_kwh"]))\
                .tag("unit", "kWh")\
                .time(now, WritePrecision.NS)
            write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)
            
            point = Point("total_power_import_t2")\
                .field("value", Decimal(data["total_power_import_t2_kwh"]))\
                .tag("unit", "kWh")\
                .time(now, WritePrecision.NS)
            write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)
            
            point = Point("total_power_export_t1")\
                .field("value", Decimal(data["total_power_export_t1_kwh"]))\
                .tag("unit", "kWh")\
                .time(now, WritePrecision.NS)
            write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)
            
            point = Point("total_power_export_t2")\
                .field("value", Decimal(data["total_power_export_t2_kwh"]))\
                .tag("unit", "kWh")\
                .time(now, WritePrecision.NS)
            write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)
        except Exception as e:
            print("Error sending power data", e)

        try:
            point = Point("total_gas")\
                .field("value", Decimal(data["total_gas_m3"]))\
                .tag("unit", "M3")\
                .time(now, WritePrecision.NS)
            write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)
        except Exception as e:
            print("Error sending gas data", e)

        time.sleep(1)