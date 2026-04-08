from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, DateTime, Text
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String)  # 'admin' or 'seller'
    is_active = Column(Boolean, default=True)

    customers = relationship("Customer", back_populates="seller")
    orders = relationship("Order", back_populates="seller")

class Customer(Base):
    __tablename__ = "customers"

    whatsapp_id = Column(String, primary_key=True, index=True) # Used as ID
    name = Column(String)
    email = Column(String, nullable=True)
    address = Column(Text)
    location_pin = Column(String, nullable=True)
    cartons_qty = Column(Integer, default=1)
    periodicity = Column(String) # 'Semanal', 'Mensual'
    payment_method = Column(String) # e.g., 'Cash', 'Sinpe'
    is_active = Column(Boolean, default=True)
    status_changed_at = Column(DateTime, nullable=True)
    
    # Context for AI Agent
    last_message_content = Column(Text, nullable=True)
    last_message_ts = Column(DateTime, nullable=True)
    n8n_context = Column(Text, nullable=True)
    
    # Pending Receipt Context
    pending_receipt_media_id = Column(String, nullable=True)
    pending_receipt_caption = Column(Text, nullable=True)
    pending_receipt_ts = Column(DateTime, nullable=True)
    pending_receipt_for_order_id = Column(Integer, nullable=True)
    
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    seller = relationship("User", back_populates="customers")
    orders = relationship("Order", back_populates="customer")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(String, ForeignKey("customers.whatsapp_id"))
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    quantity = Column(Integer)
    total_amount = Column(Float)
    payment_method = Column(String, default="Efectivo") # Added for specific sale record
    status = Column(String, default="pending") # pending, delivered, paid
    delivery_day = Column(String, nullable=True)
    delivery_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Receipt / Payment Proof
    has_attachment = Column(Boolean, default=False)
    receipt_media_id = Column(String, nullable=True)
    receipt_caption = Column(Text, nullable=True)

    customer = relationship("Customer", back_populates="orders")
    seller = relationship("User", back_populates="orders")

class Config(Base):
    __tablename__ = "configs"
    
    key = Column(String, primary_key=True, index=True)
    value = Column(String)

class MarketingTemplate(Base):
    __tablename__ = "marketing_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    meta_id = Column(String, unique=True, index=True)
    name = Column(String)
    language = Column(String)
    components = Column(Text) # JSON string of template structure
    status = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    campaigns = relationship("Campaign", back_populates="template")

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    template_id = Column(Integer, ForeignKey("marketing_templates.id"))
    variables_mapping = Column(Text, nullable=True) # JSON dictionary {"1": "name", etc}
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="draft") # draft, running, completed
    
    template = relationship("MarketingTemplate", back_populates="campaigns")
    recipients = relationship("CampaignRecipient", back_populates="campaign")

class CampaignRecipient(Base):
    __tablename__ = "campaign_recipients"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    whatsapp_id = Column(String, ForeignKey("customers.whatsapp_id"))
    status = Column(String, default="pending") # pending, sent, failed
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    
    campaign = relationship("Campaign", back_populates="recipients")
    customer = relationship("Customer")
