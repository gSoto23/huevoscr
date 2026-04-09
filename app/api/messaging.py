from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .. import database, models, auth
from ..services.whatsapp import WhatsAppService
from ..services import conversation as conversation_service
from datetime import datetime

router = APIRouter(
    prefix="/messages",
    tags=["Messaging"]
)

class OutboundMessage(BaseModel):
    to: str
    body: str
    # type: str = "text" (Future support for templates)

@router.post("/send")
async def send_whatsapp_message(
    payload: OutboundMessage,
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    # Require generic token auth (Admin or Seller or just active user)
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """
    Sends a WhatsApp message via Graph API and logs it.
    """
    service = WhatsAppService()
    
    try:
        if "[BOTONES_CONFIRMAR]" in payload.body:
            clean_body = payload.body.replace("[BOTONES_CONFIRMAR]", "").strip()
            buttons = [
                {"id": "confirm_order_yes", "title": "✅ Sí, confirmar"},
                {"id": "confirm_order_no", "title": "❌ Modificar pedido"}
            ]
            response = await service.send_interactive_buttons(payload.to, clean_body, buttons)
            payload.body = clean_body
        else:
            # 1. Send via Graph API
            response = await service.send_message(payload.to, payload.body)
        
        # 2. Log Outbound Message
        msg_data = {
            "whatsapp_id": payload.to,
            "customer_name": None, # Should already exist
            "direction": "outgoing",
            "content": payload.body,
            "timestamp": datetime.utcnow().isoformat(),
            "media_url": None,
            "type": "text",
            "sender": "bot"
        }
        
        # We can use background task to log if we want faster API response
        background_tasks.add_task(conversation_service.process_conversation_messages, db, [msg_data])
        
        return {"status": "sent", "api_response": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
