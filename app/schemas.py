from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# --- User (Admin/Seller) Schemas ---
class UserBase(BaseModel):
    username: str
    role: str # 'admin', 'seller'

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool

    class Config:
        orm_mode = True

# --- Customer Schemas ---
class CustomerBase(BaseModel):
    whatsapp_id: str
    name: str
    email: Optional[EmailStr] = None
    address: str
    location_pin: Optional[str] = None
    cartons_qty: int = 1
    periodicity: str
    payment_method: str

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    whatsapp_id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    location_pin: Optional[str] = None
    cartons_qty: Optional[int] = None
    periodicity: Optional[str] = None
    payment_method: Optional[str] = None
    seller_id: Optional[int] = None
    is_active: Optional[bool] = None

class Customer(CustomerBase):
    is_active: bool
    status_changed_at: Optional[datetime] = None
    seller_id: Optional[int] = None
    seller: Optional[User] = None

    class Config:
        orm_mode = True

# --- Order Schemas ---
class OrderBase(BaseModel):
    quantity: int
    total_amount: float
    status: Optional[str] = "pending"
    payment_method: Optional[str] = "Efectivo"
    notes: Optional[str] = None

class OrderCreate(OrderBase):
    customer_id: str
    created_at: Optional[datetime] = None  # Allow agent to backdate/specify date if needed

class Order(OrderBase):
    id: int
    customer_id: str
    seller_id: Optional[int] = None
    created_at: datetime
    status: str

    class Config:
        orm_mode = True
