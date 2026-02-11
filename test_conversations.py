import urllib.request
import urllib.parse
import json
import time

BASE_URL = "http://localhost:8000"

def get_token():
    url = f"{BASE_URL}/token"
    data = urllib.parse.urlencode({"username": "admin", "password": "admin"}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                body = json.loads(response.read().decode())
                return body["access_token"]
    except Exception as e:
        print(f"Login failed: {e}")
        return None

def send_conversation(token, payload):
    url = f"{BASE_URL}/conversations/"
    data = json.dumps(payload).encode()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Status: {response.status}")
            print(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Error: {e.code} {e.reason}")
        print(e.read().decode())
    except Exception as e:
        print(f"Request failed: {e}")

def check_customer(token, wa_id):
    url = f"{BASE_URL}/customers/"
    headers = {"Authorization": f"Bearer {token}"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            customers = json.loads(response.read().decode())
            target = next((c for c in customers if c["whatsapp_id"] == wa_id), None)
            if target:
                ctx = target.get("n8n_context", "") or ""
                print(f"Context Length: {len(ctx)}")
                print(f"Context Content:\n{ctx}")
            else:
                print("Customer not found")
    except Exception as e:
        print(f"Check failed: {e}")

def main():
    token = get_token()
    if not token:
        print("No token")
        return

    wa_id = "50699998888"
    
    # 1. First Message
    p1 = {
        "conversation_data": {
            "message_type": "text",
            "message_text": "First Message",
            "sender_id": wa_id,
            "direction": "incoming",
            "timestamp": "2024-01-01T10:00:00Z"
        },
        "whatsapp_id": wa_id,
        "customer_name": "Test Append Lib"
    }
    print("Sending 1...")
    send_conversation(token, p1)
    
    time.sleep(1)
    
    # 2. Second Message
    p2 = {
        "conversation_data": {
            "message_type": "text",
            "message_text": "Second Message",
            "sender_id": "assistant",
            "direction": "outgoing",
            "timestamp": "2024-01-01T10:01:00Z"
        },
        "whatsapp_id": wa_id,
        "customer_name": "Test Append Lib"
    }
    print("Sending 2...")
    send_conversation(token, p2)
    
    print("Checking result...")
    check_customer(token, wa_id)

if __name__ == "__main__":
    main()
