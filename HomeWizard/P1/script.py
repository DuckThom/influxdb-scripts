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
            point = Point("active_power")\
                .field("total", int(data["active_power_w"]))\
                .field("l1", int(data["active_power_l1_w"]))\
                .field("l2", int(data["active_power_l2_w"]))\
                .field("l3", int(data["active_power_l3_w"]))\
                .tag("unit", "W")\
                .time(now, WritePrecision.NS)
            write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)

            
            import_t1 = float(data["total_power_import_t1_kwh"])
            import_t2 = float(data["total_power_import_t2_kwh"])
            point = Point("total_power_import")\
                .field("total", Decimal(import_t1 + import_t2))\
                .field("t1", Decimal(import_t1))\
                .field("t2", Decimal(import_t2))\
                .tag("unit", "kWh")\
                .time(now, WritePrecision.NS)
            write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)

            
            export_t1 = float(data["total_power_export_t1_kwh"])
            export_t2 = float(data["total_power_export_t2_kwh"])
            point = Point("total_power_export")\
                .field("total", Decimal(export_t1 + export_t2))\
                .field("t1", Decimal(export_t1))\
                .field("t2", Decimal(export_t2))\
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