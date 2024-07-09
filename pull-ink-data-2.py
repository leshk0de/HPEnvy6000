import requests
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime, timezone
from dotenv import load_dotenv  

load_dotenv()


PRINTER_ADDRESS = os.getenv("PRINTER_ADDRESS")

if PRINTER_ADDRESS is None:
    print("[ERROR] PRINTER_ADDRESS environment variable not set")
    exit(1)
else:
    print(f"[INFO] PRINTER_ADDRESS: {PRINTER_ADDRESS}")

if os.getenv("HTTPS") == "true":
    print("[INFO] Using HTTPS protocol")
    PRINTER_ADDRESS = "https://" + PRINTER_ADDRESS
else:
    print("[INFO] Using HTTP protocol")
    PRINTER_ADDRESS = "http://" + PRINTER_ADDRESS


# Function to save data to a file
def save_data_to_file(data):
    # Generate filename with current date and time
    filename = datetime.now().strftime("%Y-%m-%d-%H%M") + ".json"
    # Define the path to the data directory and the filename
    filepath = f"data/{filename}"
    print(f"[INFO] Saving data to {filepath} - {(json.dumps(data) )}")
    # Write data to the file in JSON format
    with open(filepath, "w") as file:
        json.dump(data, file)


def save_data_to_influxdb(data):
    import influxdb_client, os, time
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS

    
    token = os.environ.get("INFLUXDB_TOKEN")
    print(f"[INFO] Token: {token}")
    org = os.environ.get("INFLUXDB_ORG")
    url = os.environ.get("INFLUXDB_URL")

    print(f"[INFO] Saving data to InfluxDB ({url})")
    write_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org, verify_ssl=False)
    write_api = write_client.write_api(write_options=SYNCHRONOUS)
    INFLUXDB_BUCKET=os.environ.get("INFLUXDB_BUCKET")

    if 'ink_levels_CyanMagentaYellow' not in data:
        data["ink_levels_CyanMagentaYellow"] = 0
    if 'ink_levels_Black' not in data:
        data["ink_levels_Black"] = 0

    # Create a point with the specified data
    point = Point("printer_ink_levels") \
        .tag("host", f"{PRINTER_ADDRESS}") \
        .field("ink_levels_CyanMagentaYellow", data["ink_levels_CyanMagentaYellow"]) \
        .field("ink_levels_Black", data["ink_levels_Black"]) \
        .field("total_pages", data["total_pages"]) \
        .field("bw_pages", data["bw_pages"]) \
        .field("color_pages", data["color_pages"]) \
        .time(datetime.now(timezone.utc), WritePrecision.NS)

    # Write the point to the specified bucket
    write_api.write(bucket=INFLUXDB_BUCKET, org=org, record=point)

    print("[INFO] Data written successfully.")
    

    query_api = write_client.query_api()

    query = """from(bucket: "hpenvy6000")
    |> range(start: -10m)
    |> filter(fn: (r) => r._measurement == "measurement1")"""
    tables = query_api.query(query, org="leshka-network")

    for table in tables:
        for record in table.records:
            print(record)

    write_client.close()

import requests
import xml.etree.ElementTree as ET

def get_printer_data(url):
    print(f"[INFO] Fetching data from {url}")
    response = requests.get(url, verify=False)  # Setting verify=False to ignore SSL certificate warnings
    data = {}

    # Check if the request was successful
    if response.status_code == 200:
        try:
            # Parse the XML content
            root = ET.fromstring(response.content)
        except ET.ParseError as e:
            print(f"Error: Failed to parse XML - {e}")
            return None

        # Extract ink levels
        ink_levels = {}
        for consumable in root.findall(".//pudyn:Consumable", namespaces={"pudyn": "http://www.hp.com/schemas/imaging/con/ledm/productusagedyn/2007/12/11"}):
            try:
                marker_color = consumable.find("dd:MarkerColor", namespaces={"dd": "http://www.hp.com/schemas/imaging/con/dictionaries/1.0/"}).text
                percentage_remaining = consumable.find("dd:ConsumableRawPercentageLevelRemaining", namespaces={"dd": "http://www.hp.com/schemas/imaging/con/dictionaries/1.0/"}).text

                if marker_color is not None and percentage_remaining is not None:
                    try:
                        # Convert percentage_remaining to integer
                        percentage_remaining_int = int(percentage_remaining)
                        ink_levels[marker_color] = percentage_remaining
                        data[f"ink_levels_{marker_color}"] = percentage_remaining_int
                    except ValueError:
                        print(f"Error: Unable to convert percentage remaining '{percentage_remaining}' to an integer for marker color '{marker_color}'")
                else:
                    print(f"Error: Missing marker color or percentage remaining for consumable")
            except AttributeError as e:
                print(f"Error: Failed to retrieve marker color or percentage remaining - {e}")

        # Extract printing statistics
        try:
            data["total_pages"] = int(root.find(".//dd:TotalImpressions", namespaces={"dd": "http://www.hp.com/schemas/imaging/con/dictionaries/1.0/"}).text)
        except (AttributeError, ValueError) as e:
            print(f"Error: Failed to retrieve or convert total pages - {e}")
            data["total_pages"] = None

        try:
            data["bw_pages"] = int(root.find(".//dd:MonochromeImpressions", namespaces={"dd": "http://www.hp.com/schemas/imaging/con/dictionaries/1.0/"}).text)
        except (AttributeError, ValueError) as e:
            print(f"Error: Failed to retrieve or convert monochrome pages - {e}")
            data["bw_pages"] = None

        try:
            data["color_pages"] = int(root.find(".//dd:ColorImpressions", namespaces={"dd": "http://www.hp.com/schemas/imaging/con/dictionaries/1.0/"}).text)
        except (AttributeError, ValueError) as e:
            print(f"Error: Failed to retrieve or convert color pages - {e}")
            data["color_pages"] = None

        return data
    else:
        print(f"Failed to retrieve data: {response.status_code}")
        return None

# Example usage:
# url = "http://printer_ip_address_here"
# printer_data = get_printer_data(url)
# print(printer_data)


# URL of the printer's XML data
url = f"{PRINTER_ADDRESS}/DevMgmt/ProductUsageDyn.xml"

# Get printer data
data = get_printer_data(url)



# Print printer data
if data:
    save_data_to_file(data)
    save_data_to_influxdb(data)
