
import sys
import os
import json
from datetime import datetime

# Add app directory to path
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models import Customer
from app.core import config

def check_messages():
    db = SessionLocal()
    try:
        # Find customer with the most recent activity
        customer = db.query(Customer).order_by(Customer.last_message_ts.desc()).first()
        
        if not customer:
            print("No customers found in database.")
            return

        print(f"\n--- ÚLTIMO MENSAJE RECIBIDO ---")
        print(f"Cliente: {customer.name} ({customer.whatsapp_id})")
        print(f"Hora: {customer.last_message_ts}")
        print(f"Contenido: {customer.last_message_content}")
        print(f"Contexto AI (Últimas líneas):")
        if customer.n8n_context:
            lines = customer.n8n_context.split('\n')[-5:]
            for line in lines:
                print(f"  {line}")
        print("-" * 30 + "\n")

    except Exception as e:
        print(f"Error checking database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_messages()
