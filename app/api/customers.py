from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from .. import database, models, schemas, auth

router = APIRouter(
    prefix="/customers",
    tags=["Customers"]
)

# --- Public Endpoints ---

@router.post("/public", response_model=schemas.Customer)
def public_register_or_update_customer(customer: schemas.CustomerCreate, db: Session = Depends(database.get_db)):
    # Check if customer exists by WhatsApp ID
    db_customer = db.query(models.Customer).filter(models.Customer.whatsapp_id == customer.whatsapp_id).first()
    
    if db_customer:
        # Update existing
        for key, value in customer.dict(exclude_unset=True).items():
            setattr(db_customer, key, value)
    else:
        # Create new
        db_customer = models.Customer(**customer.dict())
        db.add(db_customer)
    
    try:
        db.commit()
        db.refresh(db_customer)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
        
    return db_customer

# --- Protected Endpoints ---

@router.post("/", response_model=schemas.Customer)
def create_customer(
    customer: schemas.CustomerCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    # Check allowed roles (Admin and Seller)
    # Seller creates -> Auto assigned
    # Admin creates -> Unassigned (default)
    
    # Check if customer exists (Smart Lookup)
    # Try exact match first
    db_cust = db.query(models.Customer).filter(models.Customer.whatsapp_id == customer.whatsapp_id).first()
    
    # Smart Lookup (Try with/without 506)
    if not db_cust:
        if customer.whatsapp_id.startswith("506") and len(customer.whatsapp_id) > 8:
            # Try without 506
            short_id = customer.whatsapp_id[3:]
            db_cust = db.query(models.Customer).filter(models.Customer.whatsapp_id == short_id).first()
        elif len(customer.whatsapp_id) == 8:
            # Try with 506
            long_id = "506" + customer.whatsapp_id
            db_cust = db.query(models.Customer).filter(models.Customer.whatsapp_id == long_id).first()

    if db_cust:
        raise HTTPException(status_code=400, detail=f"El cliente ya existe con este WhatsApp (ID: {db_cust.whatsapp_id})")

    new_customer = models.Customer(**customer.dict())
    
    if current_user.role == "seller":
        new_customer.seller_id = current_user.id
        
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return new_customer

@router.get("/", response_model=List[schemas.Customer])
def read_customers(
    skip: int = 0, 
    limit: int = 100, 
    active: bool = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    query = db.query(models.Customer)
    if active is not None:
        query = query.filter(models.Customer.is_active == active)

    if current_user.role == "admin":
        customers = query.offset(skip).limit(limit).all()
    else:
        # Seller sees only their assigned customers
        customers = query.filter(models.Customer.seller_id == current_user.id).offset(skip).limit(limit).all()
    return customers

@router.get("/{whatsapp_id}", response_model=schemas.Customer)
def read_customer(
    whatsapp_id: str, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    # Try exact match first
    customer = db.query(models.Customer).filter(models.Customer.whatsapp_id == whatsapp_id).first()
    
    # Smart Lookup (Try with/without 506)
    if not customer:
        if whatsapp_id.startswith("506") and len(whatsapp_id) > 8:
            # Try without 506
            short_id = whatsapp_id[3:]
            customer = db.query(models.Customer).filter(models.Customer.whatsapp_id == short_id).first()
        elif len(whatsapp_id) == 8:
            # Try with 506
            long_id = "506" + whatsapp_id
            customer = db.query(models.Customer).filter(models.Customer.whatsapp_id == long_id).first()

    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Permission check
    if current_user.role != "admin" and customer.seller_id != current_user.id and customer.seller_id is not None:
         raise HTTPException(status_code=403, detail="Not authorized to view this customer")
         
    # Fetch last order context
    last_order = db.query(models.Order)\
        .filter(models.Order.customer_id == customer.whatsapp_id)\
        .order_by(models.Order.created_at.desc())\
        .first()
        
    if last_order:
        customer.last_order_summary = {
            "order_id": last_order.id,
            "created_at": last_order.created_at,
            "quantity": last_order.quantity,
            "total_amount": last_order.total_amount,
            "status": last_order.status,
            "payment_method": last_order.payment_method,
            "delivery_day": last_order.delivery_day,
            "delivery_date": last_order.delivery_date
        }
    else:
        customer.last_order_summary = None

    return customer

@router.delete("/{whatsapp_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    whatsapp_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    # 1. Find Customer
    customer = db.query(models.Customer).filter(models.Customer.whatsapp_id == whatsapp_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # 2. Delete related orders (Manual cascade if not set in DB)
    db.query(models.Order).filter(models.Order.customer_id == whatsapp_id).delete()
    
    # 3. Delete Customer
    db.delete(customer)
    db.commit()
    return None

@router.put("/{whatsapp_id}", response_model=schemas.Customer)
def update_customer(
    whatsapp_id: str, 
    customer_update: schemas.CustomerUpdate, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    # Try exact match first
    db_customer = db.query(models.Customer).filter(models.Customer.whatsapp_id == whatsapp_id).first()
    
    # Smart Lookup (Try with/without 506)
    if not db_customer:
        if whatsapp_id.startswith("506") and len(whatsapp_id) > 8:
            short_id = whatsapp_id[3:]
            db_customer = db.query(models.Customer).filter(models.Customer.whatsapp_id == short_id).first()
        elif len(whatsapp_id) == 8:
            long_id = "506" + whatsapp_id
            db_customer = db.query(models.Customer).filter(models.Customer.whatsapp_id == long_id).first()

    if db_customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Permission check: Only admin can reassign or fully edit? 
    # For now, let's assume Admin has full rights, Seller has limited rights (maybe handled in frontend or finer logic later)
    # The requirement says "Editar informacion... el sistema busca registro... permite modificar".
    if current_user.role != "admin" and db_customer.seller_id != current_user.id:
         raise HTTPException(status_code=403, detail="Not authorized to edit this customer")

    for key, value in customer_update.dict(exclude_unset=True).items():
        if key == "is_active" and value != db_customer.is_active:
             db_customer.status_changed_at = datetime.now()
        
        # Auto-set context timestamp if content is updated
        if key == "last_message_content":
             db_customer.last_message_ts = datetime.now()
             
        setattr(db_customer, key, value)

    db.commit()
    db.refresh(db_customer)
    return db_customer

@router.post("/assign", dependencies=[Depends(auth.get_current_admin_user)])
def assign_customer_to_seller(
    whatsapp_id: str,
    seller_id: int,
    db: Session = Depends(database.get_db)
):
    customer = db.query(models.Customer).filter(models.Customer.whatsapp_id == whatsapp_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    seller = db.query(models.User).filter(models.User.id == seller_id, models.User.role == "seller").first()
    if not seller:
         raise HTTPException(status_code=404, detail="Seller not found")
         
    customer.seller_id = seller_id
    db.commit()
    return {"status": "assigned"}

@router.post("/{whatsapp_id}/confirm_receipt", status_code=status.HTTP_200_OK)
def confirm_receipt_for_order(
    whatsapp_id: str,
    confirmation: schemas.ReceiptConfirmation,
    db: Session = Depends(database.get_db),
    # Might be called by n8n (Generic Auth? Or Public?)
    # For now, let's allow it securely via token or API key if implemented, 
    # but here let's assume valid session or internal protection.
    # If called by n8n, it needs auth. Let's use get_current_active_user (n8n should use Admin/System token)
    current_user: models.User = Depends(auth.get_current_active_user)
):
    # 1. Fetch Customer
    customer = db.query(models.Customer).filter(models.Customer.whatsapp_id == whatsapp_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # 2. Verify Pending Receipt
    if not customer.pending_receipt_media_id:
        raise HTTPException(status_code=400, detail="No pending receipt found for this customer")

    # 3. Determine Order ID
    target_order_id = confirmation.order_id or customer.pending_receipt_for_order_id
    
    if not target_order_id:
         raise HTTPException(status_code=400, detail="No target order specified or found in pending context")

    # 4. Fetch Order
    order = db.query(models.Order).filter(models.Order.id == target_order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {target_order_id} not found")

    # 5. Attach Receipt & Update Status
    order.receipt_media_id = customer.pending_receipt_media_id
    order.receipt_caption = customer.pending_receipt_caption
    order.has_attachment = True
    order.status = "payment_pending_validation" # State change for verification

    # 6. Clear Customer Pending State
    customer.pending_receipt_media_id = None
    customer.pending_receipt_caption = None
    customer.pending_receipt_ts = None
    customer.pending_receipt_for_order_id = None

    db.commit()
    
    return {
        "status": "success", 
        "message": f"Receipt attached to Order #{order.id}",
        "order_status": order.status
    }
