import requests
import xml.etree.ElementTree as ET

def get_printer_ink_levels(url):
    # Send a request to the URL
    response = requests.get(url, verify=False)  # Setting verify=False to ignore SSL certificate warnings
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the XML content
        root = ET.fromstring(response.content)
        
        # Extract ink levels
        ink_levels = {}
        for consumable in root.findall(".//pudyn:Consumable", namespaces={"pudyn": "http://www.hp.com/schemas/imaging/con/ledm/productusagedyn/2007/12/11"}):
            marker_color = consumable.find("dd:MarkerColor", namespaces={"dd": "http://www.hp.com/schemas/imaging/con/dictionaries/1.0/"}).text
            percentage_remaining = consumable.find("dd:ConsumableRawPercentageLevelRemaining", namespaces={"dd": "http://www.hp.com/schemas/imaging/con/dictionaries/1.0/"}).text
            ink_levels[marker_color] = percentage_remaining
        
        return ink_levels
    else:
        print(f"Failed to retrieve data: {response.status_code}")
        return None

# URL of the printer's XML data
url = "http://192.168.1.26/DevMgmt/ProductUsageDyn.xml"

# Get ink levels
ink_levels = get_printer_ink_levels(url)

# Print ink levels
if ink_levels:
    for color, level in ink_levels.items():
        print(f"{color}: {level}% remaining")
