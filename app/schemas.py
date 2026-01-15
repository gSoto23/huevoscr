from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

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

class CustomerUpdate(CustomerBase):
    pass

class Customer(CustomerBase):
    is_active: bool
    seller_id: Optional[int] = None

    class Config:
        orm_mode = True

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

# --- Order Schemas ---
class OrderBase(BaseModel):
    quantity: int
    total_amount: float
    notes: Optional[str] = None

class OrderCreate(OrderBase):
    customer_id: str

class Order(OrderBase):
    id: int
    customer_id: str
    seller_id: Optional[int] = None
    created_at: datetime
    status: str

    class Config:
        orm_mode = True
