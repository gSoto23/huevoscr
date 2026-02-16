
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.auth import create_access_token
from app import models, database
from datetime import timedelta

client = TestClient(app)

def create_test_order(customer_id, payload):
    # 1. Get an Admin User for Auth (or Seller)
    db = database.SessionLocal()
    admin_user = db.query(models.User).filter(models.User.role == "admin").first()
    
    if not admin_user:
        print("ERROR: No admin user found for authentication.")
        db.close()
        return

    # Generate token
    token = create_access_token(
        data={"sub": admin_user.username, "role": admin_user.role},
        expires_delta=timedelta(minutes=30)
    )
    headers = {"Authorization": f"Bearer {token}"}
    db.close()

    print(f"Sending Order for Customer: {customer_id}")
    print(f"URL: /sales/")
    print(f"Payload: {payload}")

    try:
        response = client.post("/sales/", json=payload, headers=headers)
        print(f"\nResponse Code: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
        if response.status_code == 200:
            print("\nSUCCESS: Order Created!")
        else:
            print(f"\nFAILURE: {response.text}")
            
    except Exception as e:
        print(f"\nCRASH: {str(e)}")

if __name__ == "__main__":
    # Test Data provided by user
    target_customer = "50670465000"
    
    # Payload provided by user (slightly adapted for correct JSON)
    test_payload = {
        "customer_id": target_customer,
        "quantity": 1,
        "payment_method": "Sinpe",
        "total_amount": 3000,
        "delivery_status": "pending",
        "delivery_date": "2026-02-19",
        "delivery_day": "Jueves",
        "seller_id": None
    }
    
    create_test_order(target_customer, test_payload)
