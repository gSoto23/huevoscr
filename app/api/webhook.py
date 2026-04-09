from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from .. import database, models
from ..core import config
from ..services import conversation as conversation_service
from ..services.whatsapp import WhatsAppService
import hashlib
import hmac
import httpx
import json
import logging
import os

router = APIRouter(
    prefix="/webhook",
    tags=["WhatsApp Webhook"]
)

# Set logging
logger = logging.getLogger(__name__)

VERIFY_TOKEN = config.settings.WHATSAPP_VERIFY_TOKEN
if not VERIFY_TOKEN or VERIFY_TOKEN == "my-secret-verify-token":
    logger.warning("SECURITY ALERT: WHATSAPP_VERIFY_TOKEN is using a weak fallback or is not set.")

@router.get("")
async def verify_webhook(request: Request):
    """
    Handles Meta's Verification Challenge.
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    # Debug logs visible in terminal
    logger.info(f"Webhook Verification Request -> Mode: {mode}, Token: {token}, Challenge: {challenge}")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            logger.info("WEBHOOK_VERIFIED")
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(content=challenge)
        else:
            logger.warning(f"Verification Failed. Token mismatch.")
            raise HTTPException(status_code=403, detail="Verification failed")
    
    return {"status": "ok", "message": "Webhook provider ready. Verify Token configured."}

async def forward_to_n8n(message_data: dict, db: Session):
    """
    Forwards the processed message to n8n for AI handling.
    """
    n8n_url = os.getenv("N8N_WEBHOOK_URL")
    logger.debug(f"n8n_url={n8n_url}")
    if not n8n_url:
        logger.warning("N8N_WEBHOOK_URL not set. Skipping AI.")
        return

    # We might want to send more context here, or just the primitive message
    # Let's send a structured payload
    # Prepare payload with full media URL if present
    base_url = "https://www.huevoscr.com"
    media_url = message_data.get("media_url")
    if media_url and media_url.startswith("/"):
        media_url = f"{base_url}{media_url}"

    payload = {
        "message": message_data["content"],
        "sender": message_data["whatsapp_id"],
        "timestamp": message_data["timestamp"],
        "media_url": media_url,
        "is_receipt_candidate": message_data.get("is_receipt_candidate", False),
        "pending_order_id": message_data.get("pending_order_id"),
    }
    
    try:
        logger.info(f"Forwarding message from {payload['sender']} to n8n ({n8n_url})...")
        async with httpx.AsyncClient() as client:
            resp = await client.post(n8n_url, json=payload, timeout=10.0)
            logger.info(f"n8n Response: {resp.status_code} - {resp.text}")
    except Exception as e:
        logger.error(f"Failed to forward to n8n: {e}", exc_info=True)

@router.post("")
async def receive_whatsapp_message(
    request: Request, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db)
):
    """
    Receives events from Meta.
    """
    try:
        body = await request.json()
        logger.info(f"WEBHOOK BODY RECEIVED: {json.dumps(body)}")

        # 1. Validate signature 
        if config.settings.WHATSAPP_APP_SECRET:
            signature = request.headers.get("X-Hub-Signature-256")
            if not signature:
                logger.warning("No Webhook signature provided")
            else:
                # Remove 'sha256=' prefix
                signature = signature.replace("sha256=", "")
                # Calculate HMAC
                expected_signature = hmac.new(
                    bytes(config.settings.WHATSAPP_APP_SECRET, 'latin-1'),
                    msg=await request.body(),
                    digestmod=hashlib.sha256
                ).hexdigest()
                
                if not hmac.compare_digest(signature, expected_signature):
                    logger.error("Invalid Webhook Signature")
                    raise HTTPException(status_code=403, detail="Invalid signature")


        # 2. Parse Entry
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        
        if "messages" not in value:
            # Maybe a status update (sent/delivered/read)
            return {"status": "ignored", "type": "status_update"}
            
        message = value["messages"][0]
        contact = value["contacts"][0] if "contacts" in value else {}
        
        # Extract fields
        wa_id = contact.get("wa_id") or message.get("from")
        name = contact.get("profile", {}).get("name")
        
        msg_type = message.get("type")
        timestamp = message.get("timestamp") # Unix timestamp usually
        
        # Convert unix timestamp to ISO
        if timestamp:
            from datetime import datetime
            ts_iso = datetime.utcfromtimestamp(int(timestamp)).isoformat()
        else:
            ts_iso = datetime.utcnow().isoformat()

        content = ""
        media_url = None

        # Initialize WhatsApp Service
        wa_service = WhatsAppService()
        from ..core import utils

        if msg_type == "text":
            content = message["text"]["body"]
        elif msg_type in ["image", "audio", "video", "document", "sticker"]:
            media_data = message[msg_type]
            media_id = media_data.get("id")
            caption = media_data.get("caption", "")
            
            # Fetch URL from Graph API
            temp_url = await wa_service.get_media_url(media_id)
            
            if temp_url:
                # Download to local
                local_path = await utils.download_whatsapp_image(temp_url, folder="whatsapp_media")
                media_url = local_path
                content = f"[{msg_type.upper()}] {caption}"
            else:
                content = f"[{msg_type.upper()} - DOWNLOAD FAILED] {caption}"
                logger.error(f"Failed to get URL for media ID: {media_id}")

        elif msg_type == "location":
            loc_data = message.get("location", {})
            lat = loc_data.get("latitude", "")
            lng = loc_data.get("longitude", "")
            addr_name = loc_data.get("name", "")
            addr_text = loc_data.get("address", "")
            maps_url = f"https://maps.google.com/?q={lat},{lng}"
            
            content = f"[UBICACIÓN ENVIADA: {maps_url}]"
            if addr_name or addr_text:
                content += f" | {addr_name} - {addr_text}"
            content += "\n[SYSTEM INSTRUCTION: El sistema YA GUARDÓ automáticamente en la base de datos este pin del mapa. Por favor infórmale amablemente al cliente que su dirección de entrega (ubicación) fue actualizada y recibida con éxito.]"

        else:
            content = f"[{msg_type} message]"

        msg_data = {
            "whatsapp_id": wa_id,
            "customer_name": name,
            "direction": "incoming",
            "content": content,
            "timestamp": ts_iso,
            "media_url": media_url, # None for now unless we resolve it
            "type": msg_type,
            "sender": wa_id,
            "location_pin": maps_url if msg_type == "location" else None
        }

        # 3. Process & Save
        await conversation_service.process_conversation_messages(db, [msg_data])
        
        # --- Receipt Logic ---
        # Check if this is a receipt candidate
        customer = db.query(models.Customer).filter(models.Customer.whatsapp_id == wa_id).first()
        is_receipt_candidate = False
        pending_order_id = None
        
        if customer and customer.pending_receipt_for_order_id and media_url:
            # It's a match! Stage it.
            customer.pending_receipt_media_id = media_url
            from datetime import datetime
            customer.pending_receipt_ts = datetime.utcnow()
            db.commit()
            
            is_receipt_candidate = True
            pending_order_id = customer.pending_receipt_for_order_id
            logger.info(f"Receipt Candidate Detected for Order {pending_order_id}")

        # Add flags to msg_data for n8n
        msg_data["is_receipt_candidate"] = is_receipt_candidate
        msg_data["pending_order_id"] = pending_order_id

        # 4. Trigger n8n (only for incoming user messages)
        # We use BackgroundTasks to not block the webhook response to Meta (must be < 3s)
        if getattr(customer, "ai_active", True):
            background_tasks.add_task(forward_to_n8n, msg_data, db)
        else:
            logger.info(f"AI is OFF for {wa_id}. Message saved to context but not forwarded to n8n.")

        return {"status": "processed"}
    
    except Exception as e:
        import traceback
        logger.error(f"ERROR PROCESSING WEBHOOK: {str(e)}", exc_info=True)
        # Return 200 to Meta to avoid retry loops, but log heavily
        return {"status": "error", "detail": "Webhook internal error"}
