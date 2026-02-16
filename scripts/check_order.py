
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import models, database

def check_order(order_id):
    db = database.SessionLocal()
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    
    if not order:
        print(f"Order #{order_id} not found.")
    else:
        print(f"--- Order #{order.id} ---")
        print(f"Customer: {order.customer_id}")
        print(f"Status: {order.status}")
        print(f"Total: {order.total_amount}")
        print(f"Payment Method: {order.payment_method}")
        print(f"Created At: {order.created_at}")
        
    db.close()

if __name__ == "__main__":
    target_id = 4
    if len(sys.argv) > 1:
        target_id = int(sys.argv[1])
    check_order(target_id)
