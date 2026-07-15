import requests
from requests.auth import HTTPDigestAuth

# Your device details
DEVICE_IP = "http://192.168.100.68"
USERNAME = "admin"
PASSWORD = "aa786786" # Put your real password here

# The test endpoint (asks the device for its basic info)
url = f"{DEVICE_IP}/ISAPI/System/deviceInfo"

print(f"Attempting to connect to {DEVICE_IP}...")

try:
    # Hikvision uses Digest Authentication, not basic!
    response = requests.get(url, auth=HTTPDigestAuth(USERNAME, PASSWORD), timeout=5)
    
    if response.status_code == 200:
        print("\n✅ SUCCESS! Python has successfully connected to the Hikvision machine.")
        print("Device Info Response:")
        print(response.text) # This will print the XML data with your serial number
    elif response.status_code == 401:
        print("\n❌ ERROR 401: Unauthorized. The password might be wrong, or Digest auth is failing.")
    else:
        print(f"\n⚠️ Unexpected Status Code: {response.status_code}")
        print(response.text)

except requests.exceptions.Timeout:
    print("\n❌ ERROR: Connection Timed Out. Ensure your computer is on the same Wi-Fi as the device.")
except requests.exceptions.ConnectionError:
    print("\n❌ ERROR: Connection Refused. The IP address might be wrong or the device is offline.")