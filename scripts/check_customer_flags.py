
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import models, database

def check_customer_flags(wa_id):
    db = database.SessionLocal()
    c = db.query(models.Customer).filter(models.Customer.whatsapp_id == wa_id).first()
    if c:
        print(f"Customer: {c.name} ({wa_id})")
        print(f"Pending Receipt For Order: {c.pending_receipt_for_order_id}")
        print(f"Pending Receipt Media: {c.pending_receipt_media_id}")
        print(f"Pending Timestamp: {c.pending_receipt_ts}")
        
        # Check if an order exists
        if c.pending_receipt_for_order_id:
            o = db.query(models.Order).filter(models.Order.id == c.pending_receipt_for_order_id).first()
            if o:
                print(f"Target Order #{o.id} Status: {o.status}")
                print(f"Target Order Payment Method: {o.payment_method}")
                
    # Also check Order #1 explicitly
    o1 = db.query(models.Order).filter(models.Order.id == 1).first()
    if o1:
        print(f"\n--- Order #1 Check ---")
        print(f"Order #{o1.id} Status: {o1.status}")
        print(f"Payment Method: {o1.payment_method}")
        print(f"Receipt Media ID: {o1.receipt_media_id}")
        print(f"Receipt Caption: {o1.receipt_caption}")
        print(f"Has Attachment: {o1.has_attachment}")
    else:
        print("\nOrder #1 not found")

    db.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        wa_id = sys.argv[1]
    else:
        wa_id = "50670465000" # Default debug ID
    check_customer_flags(wa_id)
