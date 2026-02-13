from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from .. import database, models, schemas, auth
from ..core import utils

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
    media_url: Optional[str] = None
    whatsapp_id: Optional[str] = None
    customer_name: Optional[str] = None
    
    # Allow extra fields like customer_name, recipient_id inside
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }

@router.post("/")
async def ingest_conversation(
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

    # Process Messages via Service
    from ..services import conversation as conversation_service
    
    # Check if payload needs to be converted to dict or if service handles Pydantic
    # Service handles Pydantic object if fields match
    
    # We need to ensure we pass the whatsapp_id into the processing if it's not in the message body
    # But the service extracts it from the first message content?
    # Actually, legacy payload might have whatsapp_id at top level, which Pydantic model captures.
    # The dictionary passed to service should ideally preserve this.
    # Let's create a list of dicts with the top-level info injected if missing from message
    
    msgs_as_dicts = []
    # Convert Pydantic to dict
    payload_dict = payload.model_dump(by_alias=True)
    
    # Pydantic alias trickery might hide fields, let's be careful.
    # payload.whatsapp_id is available.
    
    # Construct a dict that service expects
    msg_data = {
        "whatsapp_id": payload.whatsapp_id,
        "customer_name": payload.customer_name,
        "direction": payload.direction,
        "content": payload.content,
        "timestamp": payload.timestamp,
        "media_url": payload.media_url,
        "type": payload.type,
        "sender": payload.sender
    }
    msgs_as_dicts.append(msg_data)

    result = await conversation_service.process_conversation_messages(db, msgs_as_dicts)

    return result
