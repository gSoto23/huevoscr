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
    
    db_cust = db.query(models.Customer).filter(models.Customer.whatsapp_id == customer.whatsapp_id).first()
    if db_cust:
        raise HTTPException(status_code=400, detail="El cliente ya existe con este WhatsApp")

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
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if current_user.role == "admin":
        customers = db.query(models.Customer).offset(skip).limit(limit).all()
    else:
        # Seller sees only their assigned customers
        customers = db.query(models.Customer).filter(models.Customer.seller_id == current_user.id).offset(skip).limit(limit).all()
    return customers

@router.get("/{whatsapp_id}", response_model=schemas.Customer)
def read_customer(
    whatsapp_id: str, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    customer = db.query(models.Customer).filter(models.Customer.whatsapp_id == whatsapp_id).first()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Permission check
    if current_user.role != "admin" and customer.seller_id != current_user.id:
         raise HTTPException(status_code=403, detail="Not authorized to view this customer")
         
    return customer

@router.put("/{whatsapp_id}", response_model=schemas.Customer)
def update_customer(
    whatsapp_id: str, 
    customer_update: schemas.CustomerUpdate, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_customer = db.query(models.Customer).filter(models.Customer.whatsapp_id == whatsapp_id).first()
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
