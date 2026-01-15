from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import database, models, schemas, auth

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

    db_order = models.Order(**order.dict(), seller_id=current_user.id)
    db.add(db_order)
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
