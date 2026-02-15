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

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "my-secret-verify-token")

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
    print(f"DEBUG: Webhook Verification Request -> Mode: {mode}, Token: {token}, Challenge: {challenge}")
    print(f"DEBUG: Expected Token: {config.settings.WHATSAPP_VERIFY_TOKEN}")

    if mode and token:
        if mode == "subscribe" and token == config.settings.WHATSAPP_VERIFY_TOKEN:
            print("debug: WEBHOOK_VERIFIED", flush=True)
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(content=challenge)
        else:
            print(f"DEBUG: Verification Failed. Expected {config.settings.WHATSAPP_VERIFY_TOKEN} but got {token}")
            raise HTTPException(status_code=403, detail="Verification failed")
    
    return {"status": "ok", "message": "Webhook provider ready. Verify Token configured."}

async def forward_to_n8n(message_data: dict, db: Session):
    """
    Forwards the processed message to n8n for AI handling.
    """
    n8n_url = os.getenv("N8N_WEBHOOK_URL")
    print(f"DEBUG: n8n_url={n8n_url}", flush=True)
    if not n8n_url:
        print("WARNING: N8N_WEBHOOK_URL not set. Skipping AI.", flush=True)
        return

    # We might want to send more context here, or just the primitive message
    # Let's send a structured payload
    payload = {
        "message": message_data["content"],
        "sender": message_data["whatsapp_id"],
        "timestamp": message_data["timestamp"],
        "media_url": message_data.get("media_url"),
        # Fetch latest context? Or let n8n fetch it via API?
        # Let's send minimal data first.
    }
    
    try:
        print(f"Forwarding message from {payload['sender']} to n8n ({n8n_url})...", flush=True)
        async with httpx.AsyncClient() as client:
            resp = await client.post(n8n_url, json=payload, timeout=10.0)
            print(f"n8n Response: {resp.status_code} - {resp.text}", flush=True)
    except Exception as e:
        print(f"ERROR: Failed to forward to n8n: {e}", flush=True)

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
        print(f"📩 WEBHOOK BODY RECEIVED: {json.dumps(body, indent=2)}", flush=True)

        # 1. Validate signature (Optional for now, but recommended for Prod)
        if config.settings.WHATSAPP_APP_SECRET:
            signature = request.headers.get("X-Hub-Signature-256")
            if not signature:
                # For now, warn but allow if no signature provided in dev? 
                # Or strict:
                # logger.warning("No signature provided")
                pass
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
                    print("ERROR: Invalid Webhook Signature", flush=True)
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
                print(f"ERROR: Failed to get URL for media ID: {media_id}", flush=True)

        else:
            content = f"[{msg_type} message]"

        # Construct payload for Service
        msg_data = {
            "whatsapp_id": wa_id,
            "customer_name": name,
            "direction": "incoming",
            "content": content,
            "timestamp": ts_iso,
            "media_url": media_url, # None for now unless we resolve it
            "type": msg_type,
            "sender": wa_id
        }

        # 3. Process & Save
        await conversation_service.process_conversation_messages(db, [msg_data])
        
        # 4. Trigger n8n (only for incoming user messages)
        # We use BackgroundTasks to not block the webhook response to Meta (must be < 3s)
        background_tasks.add_task(forward_to_n8n, msg_data, db)

        return {"status": "processed"}
    
    except Exception as e:
        import traceback
        error_msg = f"ERROR PROCESSING WEBHOOK: {str(e)}\n{traceback.format_exc()}"
        error_msg = f"ERROR PROCESSING WEBHOOK: {str(e)}\n{traceback.format_exc()}"
        print(error_msg, flush=True) # Print to stdout for systemctl status
        # Return 200 to Meta to avoid retry loops, but log heavily
        return {"status": "error", "detail": str(e)}
