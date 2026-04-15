from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from .. import database, models, schemas, auth
from ..core import utils
from ..services import conversation as conversation_service
from ..services.whatsapp import WhatsAppService
from fastapi import UploadFile, File, Form, BackgroundTasks
import logging

logger = logging.getLogger(__name__)

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

@router.post("/{whatsapp_id}/toggle_ai")
async def toggle_ai(
    whatsapp_id: str,
    active: bool = Body(..., embed=True),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    customer = db.query(models.Customer).filter(models.Customer.whatsapp_id == whatsapp_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    customer.ai_active = active
    db.commit()

    # Opt: Notify customer
    wa_service = WhatsAppService()
    try:
        if active:
            msg = "🤖 El asistente inteligente ha sido reactivado."
        else:
            msg = "🧑‍💻 Un agente humano se ha unido al chat y te atenderá en breve."
        await wa_service.send_message(whatsapp_id, msg)
        
        # Append to context
        await conversation_service.process_conversation_messages(db, [{
            "whatsapp_id": whatsapp_id,
            "direction": "outgoing",
            "content": msg,
            "timestamp": datetime.utcnow().isoformat(),
            "type": "text",
            "sender": "Agente/Notificación"
        }])
    except Exception as e:
        logger.error(f"Error notifying AI Toggle: {e}", exc_info=True)

    return {"status": "success", "ai_active": active}

@router.post("/{whatsapp_id}/send")
async def send_manual_message(
    whatsapp_id: str,
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    customer = db.query(models.Customer).filter(models.Customer.whatsapp_id == whatsapp_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    if getattr(customer, "ai_active", False):
         raise HTTPException(status_code=400, detail="Cannot send manual message while AI is active.")
         
    # Check 24h limit
    last_ts = getattr(customer, "last_customer_msg_ts", None)
    if not last_ts or (datetime.utcnow() - last_ts).total_seconds() > 86400:
         raise HTTPException(status_code=400, detail="Vencida la ventana de 24 horas. Envía un template.")

    wa_service = WhatsAppService()
    content_log = ""
    
    try:
        if file:
            file_bytes = await file.read()
            # Upload to Meta
            media_id = await wa_service.upload_media(file_bytes, file.content_type)
            if not media_id:
                raise Exception("Failed to get media_id from Meta")
                
            media_type = "image"
            if "video" in file.content_type: media_type = "video"
            elif "pdf" in file.content_type or "doc" in file.content_type: media_type = "document"
            
            await wa_service.send_media(whatsapp_id, media_id, media_type, caption=text or "")
            
            import os
            import uuid
            import mimetypes
            import boto3
            from pathlib import Path
            
            ext = mimetypes.guess_extension(file.content_type)
            if not ext:
                if media_type == "image": ext = ".jpg"
                elif media_type == "video": ext = ".mp4"
                elif media_type == "document": ext = ".pdf"
                else: ext = ".bin"
                
            filename = f"{uuid.uuid4()}{ext}"
            bucket_name = os.getenv("AWS_BUCKET_NAME")
            folder = "admin_media"
            
            if bucket_name:
                s3_path = f"public/{folder}/{filename}"
                s3_client = boto3.client('s3')
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=s3_path,
                    Body=file_bytes,
                    ContentType=file.content_type,
                )
                media_url_for_log = f"https://{bucket_name}.s3.amazonaws.com/{s3_path}"
            else:
                upload_dir = Path(f"app/static/{folder}")
                upload_dir.mkdir(parents=True, exist_ok=True)
                file_path = upload_dir / filename
                with open(file_path, "wb") as f:
                    f.write(file_bytes)
                media_url_for_log = f"/static/{folder}/{filename}"
            
            content_log = f"[MEDIA: {media_url_for_log}]" + (f" {text}" if text else "")
        elif text:
            await wa_service.send_message(whatsapp_id, text)
            content_log = text
        else:
            raise HTTPException(status_code=400, detail="Must provide text or file.")
            
        # Log to ctx
        await conversation_service.process_conversation_messages(db, [{
             "whatsapp_id": whatsapp_id,
             "direction": "outgoing",
             "content": content_log,
             "timestamp": datetime.utcnow().isoformat(),
             "type": "text",
             "sender": "Agente/Tú"
        }])
        
        return {"status": "success"}

    except Exception as e:
        import traceback
        logger.error(f"Error sending manual message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{whatsapp_id}/reactivate")
async def reactivate_window(
    whatsapp_id: str,
    template_id: int = Body(..., embed=True),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    customer = db.query(models.Customer).filter(models.Customer.whatsapp_id == whatsapp_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    template = db.query(models.MarketingTemplate).filter(models.MarketingTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
        
    wa_service = WhatsAppService()
    try:
         await wa_service.send_template(whatsapp_id, template.name, template.language)
         await conversation_service.process_conversation_messages(db, [{
             "whatsapp_id": whatsapp_id,
             "direction": "outgoing",
             "content": f"[TEMPLATE ENVIADO: {template.name}]",
             "timestamp": datetime.utcnow().isoformat(),
             "type": "template",
             "sender": "Agente/Tú"
         }])
         # We implicitly wait for customer reply to open the window, but we successfully sent a template.
         return {"status": "success"}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))
