from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from .. import models
from ..core import utils

async def process_conversation_messages(db: Session, messages: List[dict]):
    """
    Processes a list of message dictionaries (or objects convertible to dict).
    Finds/Creates the customer, downloads media, formats log, and updates n8n_context.
    """
    if not messages:
        return None

    # We assume all messages belong to the same customer/whatsapp_id for now
    first_msg = messages[0]
    target_wa_id = first_msg.get("whatsapp_id")
    target_name = first_msg.get("customer_name")

    if not target_wa_id:
        # Try finding in message object if it's a Pydantic model dump
        # But for now, we rely on sender providing it. 
        # If internal webhook, we must ensure we extract it.
        pass

    if not target_wa_id:
        raise ValueError("Missing whatsapp_id")

    # 1. Find Customer
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
        db.commit()      
        db.refresh(customer)

    # Process Messages
    formatted_log = ""
    new_content_to_add = ""
    
    for msg in messages:
        # Handle dict or Pydantic object
        direction = msg.get("direction") if isinstance(msg, dict) else msg.direction
        timestamp = msg.get("timestamp") if isinstance(msg, dict) else msg.timestamp
        content = msg.get("content") if isinstance(msg, dict) else msg.content
        media_url = msg.get("media_url") if isinstance(msg, dict) else msg.media_url

        sender_label = "Cliente" if direction == "incoming" else "Agente"
        
        # Parse timestamp
        ts_str = timestamp
        try:
            # Handle ISO 8601 with Z
            if ts_str.endswith("Z"):
                ts_str = ts_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts_str)
            ts_str = dt.strftime("%d/%m/%Y %H:%M:%S")
        except Exception as e:
            pass 

        content_line = content
        
        # Handle Media
        if media_url:
            try:
                local_path = await utils.download_whatsapp_image(media_url, folder="logs/media")
                content_line += f" [MEDIA: {local_path}]"
            except Exception as e:
                print(f"Error downloading media: {e}")
                content_line += f" [MEDIA: {media_url}]"

        line = f"[{ts_str}] {sender_label}: {content_line}"
        formatted_log += line + "\n"

    # Append to existing context with deduplication
    current_context = customer.n8n_context or ""
    
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
    last_incoming = next((m for m in reversed(messages) 
                          if (m.get("direction") if isinstance(m, dict) else m.direction) == "incoming"), None)
    
    if last_incoming:
        customer.last_message_content = last_incoming.get("content") if isinstance(last_incoming, dict) else last_incoming.content
        customer.last_customer_msg_ts = datetime.utcnow()

    db.add(customer)
    db.commit()

    return {
        "status": "success", 
        "customer_id": customer.whatsapp_id, 
        "messages_added": len(messages), 
        "new_context_len": len(customer.n8n_context)
    }
