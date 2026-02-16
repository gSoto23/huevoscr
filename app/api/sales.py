from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import database, models, schemas, auth
from ..core import utils
from datetime import datetime

router = APIRouter(
    prefix="/sales",
    tags=["Sales"]
)

@router.post("/", response_model=schemas.Order)
def create_sale(
    order: schemas.OrderCreate, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    # Verify customer exists
    customer = db.query(models.Customer).filter(models.Customer.whatsapp_id == order.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    # If seller, verify assignment or permission?
    # Requirement: "Report payments... Register payments"
    if current_user.role == "seller" and customer.seller_id != current_user.id:
        # In a strict system, we might block this. But maybe a seller is filling in for another?
        # For now, let's enforce assignment.
        raise HTTPException(status_code=403, detail="Customer not assigned to you")

    sale_data = order.dict(exclude_unset=True)
    if "created_at" not in sale_data or not sale_data["created_at"]:
        sale_data["created_at"] = datetime.now()

    # --- Agent Logic for Create ---
    # 1. Map 'delivery_status' to 'status'
    if "delivery_status" in sale_data:
        sale_data["status"] = sale_data.pop("delivery_status")

    # 2. Handle 'delivery_date'
    if "delivery_date" in sale_data and isinstance(sale_data["delivery_date"], str):
        d_str = sale_data["delivery_date"]
        try:
            dt = datetime.strptime(d_str, "%d/%m/%Y")
            sale_data["delivery_date"] = dt
        except ValueError:
            try:
                dt = datetime.strptime(d_str, "%Y-%m-%d")
                sale_data["delivery_date"] = dt
            except ValueError:
                 raise HTTPException(status_code=400, detail=f"Invalid date format: {d_str}")

    # 3. Clean up extra fields not in Order model
    # customer_name, phone, seller_name might be in schema but not model
    for field in ["customer_name", "phone", "seller_name"]:
        if field in sale_data:
            del sale_data[field]

    # 4. Handle Seller ID logic
    # If explicitly passed via API (e.g. from Agent), use it.
    real_seller_id = sale_data.get("seller_id")
    if not real_seller_id:
        # Fallback to customer's assigned seller or current user
        real_seller_id = customer.seller_id if customer.seller_id else current_user.id
    
    sale_data["seller_id"] = real_seller_id

    # 5. Handle n8n_context - REMOVED to prevent overwrite
    if "n8n_context" in sale_data:
        # We ignore it now, relying on /conversations endpoint
        # content = sale_data.pop("n8n_context")
         del sale_data["n8n_context"]

    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # --- Receipt Logic ---
    # If payment method is SINPE or Transfer, we expect a receipt.
    # We flag the customer so the next incoming image is treated as a candidate.
    try:
        pm = sale_data.get("payment_method", "").lower()
        if pm in ["sinpe", "transferencia", "deposito", "transfer"]:
            # Re-fetch customer to ensure session attachment (optional but safe)
            # customer = db.merge(customer) 
            customer.pending_receipt_for_order_id = db_order.id
            customer.pending_receipt_ts = datetime.utcnow()
            db.add(customer) # Mark modified
            db.commit()
            print(f"DEBUG: Customer {customer.whatsapp_id} flagged for receipt on Order #{db_order.id}", flush=True)
    except Exception as e:
        print(f"ERROR: Failed to flag customer for receipt: {str(e)}", flush=True)
        # We generally don't want to crash the order creation just because this failed.
        # But we should alert someone.
        db.rollback() 

    return db_order

@router.get("/{order_id}", response_model=schemas.Order)
def get_sale(
    order_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    # Permission check
    if current_user.role != "admin" and order.seller_id != current_user.id:
         raise HTTPException(status_code=403, detail="Not authorized to view this order")
         
    return order

@router.put("/{order_id}", response_model=schemas.Order)
async def update_sale(
    order_id: int,
    order_update: schemas.OrderUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Permission check: Sellers can only update their own orders. Admin can update all.
    if current_user.role != "admin" and db_order.seller_id != current_user.id:
         raise HTTPException(status_code=403, detail="Not authorized to update this order")

    # --- Logic to handle Agent specific fields ---
    update_data = order_update.dict(exclude_unset=True)

    # 1. Map 'delivery_status' to 'status'
    if "delivery_status" in update_data:
        update_data["status"] = update_data.pop("delivery_status")

    # 2. Handle 'delivery_date' string (DD/MM/YYYY or YYYY-MM-DD) -> datetime
    if "delivery_date" in update_data and isinstance(update_data["delivery_date"], str):
        d_str = update_data["delivery_date"]
        try:
            # Try DD/MM/YYYY
            dt = datetime.strptime(d_str, "%d/%m/%Y")
            update_data["delivery_date"] = dt
        except ValueError:
            try:
                # Try YYYY-MM-DD (ISO format common in JSON)
                dt = datetime.strptime(d_str, "%Y-%m-%d")
                update_data["delivery_date"] = dt
            except ValueError:
                # If both fail, remove it to prevent 500 error (or raise 400)
                # Raising 400 is clearer for the user/agent
                raise HTTPException(status_code=400, detail=f"Invalid date format for delivery_date: {d_str}. Use DD/MM/YYYY or YYYY-MM-DD")

    # 3. Handle 'seller_name' -> Look up seller_id (Best effort)
    # If seller_id is already provided in payload (schema has it now), use it.
    # If seller_name is provided, it overrides or fills seller_id.
    if "seller_name" in update_data:
        s_name = update_data.pop("seller_name")
        if s_name:
            seller = db.query(models.User).filter(models.User.username == s_name).first()
            if seller:
                update_data["seller_id"] = seller.id
    
    # 4. Handle 'customer_name' -> Update Customer record (Best effort)
    if "customer_name" in update_data:
        c_name = update_data.pop("customer_name")
        if c_name and db_order.customer:
            db_order.customer.name = c_name
            db.add(db_order.customer) # Mark as modified

    # 5. Handle 'n8n_context' -> REMOVED
    if "n8n_context" in update_data:
        del update_data["n8n_context"]

    # Remove fields that are not in Order model
    # 'phone' is likely customer_id (PK), so we don't update it easily.
    if "phone" in update_data:
        del update_data["phone"]

    # Apply updates
    for key, value in update_data.items():
        # Check if we need to download media
        if key == "receipt_media_id" and value and str(value).startswith("http"):
            # It's a URL, try to download it
            # This requires WHATSAPP_TOKEN in .env
            local_path = await utils.download_whatsapp_image(str(value))
            value = local_path
            
        if hasattr(db_order, key):
            setattr(db_order, key, value)

    db.commit()
    db.refresh(db_order)
    return db_order

@router.get("/", response_model=List[schemas.Order])
def read_sales(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if current_user.role == "admin":
        orders = db.query(models.Order).offset(skip).limit(limit).all()
    else:
        orders = db.query(models.Order).filter(models.Order.seller_id == current_user.id).offset(skip).limit(limit).all()
    return orders

@router.get("/distribution")
def generate_distribution_list(
    day: str = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    # Admin tool to generate lists
    # Logic: Get all customers where periodicity matches
    query = db.query(models.Customer).filter(models.Customer.is_active == True)
    if day: # 'day' param might need renaming to 'period' but keeping simple for now
        query = query.filter(models.Customer.periodicity == day)
    
    customers = query.all()
    
    # Group by seller
    distribution = {}
    total_cartons = 0
    
    for c in customers:
        seller_name = c.seller.username if c.seller else "Unassigned"
        if seller_name not in distribution:
            distribution[seller_name] = []
        
        distribution[seller_name].append({
            "customer": c.name,
            "address": c.address,
            "whatsapp": c.whatsapp_id,
            "qty": c.cartons_qty
        })
        total_cartons += c.cartons_qty
        
    return {
        "day": day if day else "All",
        "total_cartons": total_cartons,
        "routes": distribution
    }
