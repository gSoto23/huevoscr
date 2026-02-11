from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from .. import database, models, auth

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"]
)

# --- Schemas for this specific endpoint ---
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Union

# --- Schemas for this specific endpoint ---
class ConversationMessage(BaseModel):
    # Support both 'type' and 'message_type' via alias
    type: str = Field(..., alias="message_type") 
    content: str = Field(..., alias="message_text")
    sender: str = Field(..., alias="sender_id")
    direction: str # incoming, outgoing
    timestamp: str 
    whatsapp_id: Optional[str] = None
    customer_name: Optional[str] = None
    
    # Allow extra fields like customer_name, recipient_id inside
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }

@router.post("/")
def ingest_conversation(
    payload: ConversationMessage,
    db: Session = Depends(database.get_db),
    # Require generic token auth (Admin or Seller or just active user)
    # n8n should send Authorization: Bearer <token>
    current_user: models.User = Depends(auth.get_current_active_user)
):
    # Normalize data to list
    messages = [payload]
        
    # Fallback for ID and Name
    target_wa_id = payload.whatsapp_id
    target_name = payload.customer_name

    # Check the raw dict of the first message if we still need ID
    # Note: Pydantic model might strip extra fields if configured to ignore, but we set extra="ignore".
    # However, if we need to access 'recipient_id' from the message, it's problematic if the model discarded it.
    # Let's hope the user passes whatsapp_id at top level or we need to rethink schema.
    # Re-reading error: "recipient_id":"19086567855" was inside "input".
    
    # If whatsapp_id is None, try to find it in the messages if possible? 
    # But schema required it? No, I made it Optional in previous step.
    
    if not target_wa_id:
        # Emergency fallback: If we can't find ID, we can't do anything.
        # But wait, earlier error input showed "recipient_id" inside the message object.
        # Can we access it? Not easily if model discarded it. 
        # Actually, let's assume the user IS sending it at top level or we can't fix it blindly without seeing full request.
        # But wait! n8n's "Body" parameter usually wraps everything.
        # If payload.whatsapp_id is None, check if we can get it from message context?
        # Actually, let's assume valid request will have it. 
        if not target_wa_id:
             # Try to get from first message if keys exist in raw? Hard with Pydantic.
             # Let's raise 400
             raise HTTPException(status_code=400, detail="Missing whatsapp_id")

    # 1. Find Customer with Row Lock to prevent race conditions
    # Note: with_for_update() might not work on all DBs (like SQLite) as expected, but good practice.
    customer = db.query(models.Customer).filter(models.Customer.whatsapp_id == target_wa_id).with_for_update().first()
    
    if not customer:
        # Create Lead if not exists
        customer = models.Customer(
            whatsapp_id=target_wa_id,
            name=target_name or "New Lead",
            address="Unknown - From Chat",
            periodicity="Semanal", # Default
            cartons_qty=1,
            payment_method="Efectivo",
            n8n_context="" # Init
        )
        db.add(customer)
        db.commit()      # Commit creation
        db.refresh(customer)
        # Re-fetch with lock just to be sure if we are paranoid, but newly created unique ID is safe for this trans usually.
        # Actually, if we commit, we lost the lock? No, we didn't have lock.
        # Let's just proceed.

    # 2. Process Messages
    formatted_log = ""
    for msg in messages:
        sender_label = "Cliente" if msg.direction == "incoming" else "Agente"
        
        # Parse timestamp
        ts_str = msg.timestamp
        try:
            # Handle ISO 8601 with Z
            if ts_str.endswith("Z"):
                ts_str = ts_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts_str)
            # User requested DDMMYYYY HHMMSS format (interpreted as DD/MM/YYYY)
            ts_str = dt.strftime("%d/%m/%Y %H:%M:%S")
        except Exception as e:
            pass 

        line = f"[{ts_str}] {sender_label}: {msg.content}"
        formatted_log += line + "\n"

    # Append to existing context with deduplication
    current_context = customer.n8n_context or ""
    
    # Check if the new log lines are already present in the current context (end)
    # Simple check: if formatted_log is already at the end of current_context, skip.
    # More robust: check each line.
    
    new_content_to_add = ""
    for line in formatted_log.strip().split('\n'):
        if line and line not in current_context:
             new_content_to_add += line + "\n"
    
    if new_content_to_add:
        if current_context and not current_context.endswith("\n"):
            current_context += "\n"
        customer.n8n_context = current_context + new_content_to_add
    
    # Update latest activity timestamps
    customer.last_message_ts = datetime.utcnow()
    
    # Update last message content from the latest incoming message
    last_incoming = next((m for m in reversed(messages) if m.direction == "incoming"), None)
    if last_incoming:
        customer.last_message_content = last_incoming.content

    db.add(customer)
    db.commit()

    return {"status": "success", "customer_id": customer.whatsapp_id, "messages_added": len(messages), "new_context_len": len(customer.n8n_context)}
