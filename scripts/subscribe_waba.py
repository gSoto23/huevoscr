import os
import requests
from dotenv import load_dotenv

# Load .env explicitly
load_dotenv("/Users/gsoto/Desktop/huevoscr/.env")

TOKEN = os.getenv("WHATSAPP_TOKEN")
# Hardcoding the ID since it might not be in .env yet, but user provided it.
# Ideally it should be in .env
WABA_ID = os.getenv("WHATSAPP_ACCOUNT_ID", "1626192541887007")

print(f"Subscribing App to WABA ID: {WABA_ID}")

if not TOKEN or TOKEN.startswith("TU_TOKEN"):
    print("Error: WHATSAPP_TOKEN no valido en config.")
    exit(1)

url = f"https://graph.facebook.com/v18.0/{WABA_ID}/subscribed_apps"
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

try:
    # 1. Check existing subscriptions
    print("Checking existing subscriptions...")
    get_res = requests.get(url, headers=headers)
    print(f"GET Status: {get_res.status_code}")
    print(f"GET Response: {get_res.text}")

    # 2. Subscribe (POST)
    print("\nSubscribing...")
    response = requests.post(url, headers=headers)
    print(f"POST Status: {response.status_code}")
    print(f"POST Response: {response.text}")
    
    if response.status_code == 200 and "success" in response.text:
        print("\nSUCCESS: App subscribed to WABA!")
    else:
        print("\nFAILED to subscribe.")

except Exception as e:
    print(f"\nError executing request: {e}")
