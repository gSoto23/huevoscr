
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import models, database
from datetime import datetime

def fix_order_receipt_flag(order_id):
    db = database.SessionLocal()
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    
    if not order:
        print(f"ERROR: Order #{order_id} not found.")
        db.close()
        return

    print(f"Found Order #{order.id} | Status: {order.status} | Payment Method: {order.payment_method}")
    
    # Check Customer
    if not order.customer:
         print(f"ERROR: Order #{order.id} has no customer associated.")
         db.close()
         return

    customer = order.customer
    print(f"Customer: {customer.name} ({customer.whatsapp_id})")
    
    # Force set flag
    customer.pending_receipt_for_order_id = order.id
    customer.pending_receipt_ts = datetime.utcnow()
    
    db.commit()
    print(f"SUCCESS: Customer {customer.whatsapp_id} flagged to expect receipt for Order #{order.id}.")
    print("Next image sent by this customer will be treated as receipt candidate.")
    
    db.close()

if __name__ == "__main__":
    target_id = 1
    if len(sys.argv) > 1:
        target_id = int(sys.argv[1])
    fix_order_receipt_flag(target_id)
