from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
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
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    location_pin: Optional[str] = None
    cartons_qty: Optional[int] = 1
    periodicity: Optional[str] = None
    payment_method: Optional[str] = None

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
    last_message_content: Optional[str] = None
    last_message_ts: Optional[datetime] = None
    pending_receipt_media_id: Optional[str] = None
    pending_receipt_caption: Optional[str] = None
    pending_receipt_ts: Optional[datetime] = None
    pending_receipt_for_order_id: Optional[int] = None
    n8n_context: Optional[str] = None

class Customer(CustomerBase):
    is_active: bool
    status_changed_at: Optional[datetime] = None
    last_message_content: Optional[str] = None
    last_message_ts: Optional[datetime] = None
    n8n_context: Optional[str] = None
    pending_receipt_media_id: Optional[str] = None
    pending_receipt_caption: Optional[str] = None
    pending_receipt_ts: Optional[datetime] = None
    pending_receipt_for_order_id: Optional[int] = None
    seller_id: Optional[int] = None
    seller: Optional[User] = None
    last_order_summary: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True

# --- Order Schemas ---
class OrderBase(BaseModel):
    quantity: int
    total_amount: float
    status: Optional[str] = "pending"
    payment_method: Optional[str] = "Efectivo"
    notes: Optional[str] = None
    has_attachment: Optional[bool] = False
    receipt_media_id: Optional[str] = None
    receipt_caption: Optional[str] = None

class OrderCreate(OrderBase):
    customer_id: str
    created_at: Optional[datetime] = None  # Allow agent to backdate/specify date if needed
    # Extra fields for Agent
    delivery_day: Optional[str] = None
    delivery_date: Optional[str] = None # Input as string, parsed in API
    delivery_status: Optional[str] = None
    seller_id: Optional[int] = None
    n8n_context: Optional[str] = None

class OrderUpdate(BaseModel):
    quantity: Optional[int] = None
    total_amount: Optional[float] = None
    payment_method: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    # Extra fields for AI Agent compatibility
    customer_name: Optional[str] = None
    phone: Optional[str] = None
    delivery_status: Optional[str] = None
    seller_name: Optional[str] = None
    seller_id: Optional[int] = None
    delivery_day: Optional[str] = None
    delivery_date: Optional[str] = None
    has_attachment: Optional[bool] = None
    receipt_media_id: Optional[str] = None
    receipt_caption: Optional[str] = None
    n8n_context: Optional[str] = None

class ReceiptConfirmation(BaseModel):
    order_id: Optional[int] = None

class Order(OrderBase):
    id: int
    customer_id: str
    seller_id: Optional[int] = None
    created_at: datetime
    status: str
    delivery_day: Optional[str] = None
    delivery_date: Optional[datetime] = None

    customer: Optional[Customer] = None
    seller: Optional[User] = None

    class Config:
        orm_mode = True

# --- Marketing Schemas ---
class MarketingTemplateBase(BaseModel):
    meta_id: str
    name: str
    language: str
    components: str
    status: str

class MarketingTemplateCreate(MarketingTemplateBase):
    pass

class MarketingTemplate(MarketingTemplateBase):
    id: int
    updated_at: datetime
    
    class Config:
        orm_mode = True

class CampaignCreate(BaseModel):
    name: str
    template_id: int
    variables_mapping: Optional[str] = None # JSON string

class Campaign(BaseModel):
    id: int
    name: str
    template_id: int
    variables_mapping: Optional[str] = None
    created_at: datetime
    status: str

    class Config:
        orm_mode = True

class CampaignRecipientCreate(BaseModel):
    whatsapp_id: str

class CampaignRecipientAddList(BaseModel):
    whatsapp_ids: List[str]

class CampaignRecipient(BaseModel):
    id: int
    campaign_id: int
    whatsapp_id: str
    status: str
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None

    class Config:
        orm_mode = True
