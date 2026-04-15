from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks, Body
from sqlalchemy.orm import Session
from .. import database, models
from ..core import config
from ..services import conversation as conversation_service
from ..services import tilopay as tilopay_service
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
            content += "\n[SYSTEM INSTRUCTION: El sistema YA GUARDÓ esta ubicación en la base de datos y le envió 2 botones al cliente. Por favor NO RESPONDAS a este mensaje. Mantente en silencio hasta que confirme con uno de los botones.]"

            # Enviar botones interactivos
            buttons = [
                {"id": "confirm_address_yes", "title": "✅ Sí, confirmar"},
                {"id": "confirm_address_no", "title": "❌ Nueva dirección"}
            ]
            background_tasks.add_task(
                wa_service.send_interactive_buttons,
                wa_id,
                "📍 Hemos recibido tu ubicación. ¿Confirmas que quieres registrarla como tu dirección de pedidos?",
                buttons
            )

        elif msg_type == "interactive":
            try:
                interactive_type = message.get("interactive", {}).get("type")
                if interactive_type == "button_reply":
                    btn_reply = message["interactive"]["button_reply"]
                    btn_id = btn_reply.get("id")
                    btn_title = btn_reply.get("title")
                    
                    if btn_id == "confirm_address_yes":
                        content = f"[BOTÓN CLICK: {btn_title}]\n[SYSTEM INSTRUCTION: El cliente confirmó mediante un botón que la ubicación es correcta. Confírmale de vuelta que la dirección de entrega fue guardada exitosamente y pregúntale cómo más le puedes ayudar con su pedido.]"
                    elif btn_id == "confirm_address_no":
                        content = f"[BOTÓN CLICK: {btn_title}]\n[SYSTEM INSTRUCTION: El cliente indicó que la ubicación registrada no sirve. Pídele que te comparta una mejor ubicación de GPS o que escriba su dirección manualmente para guardarla.]"
                    elif btn_id == "confirm_order_yes":
                         content = f"[BOTÓN CLICK: {btn_title}]\n[SYSTEM INSTRUCTION: El cliente acaba de confirmar su pedido mediante botón. Debes ejecutar de inmediato la creación de orden llamando a HTTP Request Crear Orden y confírmale al cliente.]"
                    elif btn_id == "confirm_order_no":
                         content = f"[BOTÓN CLICK: {btn_title}]\n[SYSTEM INSTRUCTION: El cliente rechazó confirmar su pedido mediante botón. Pídele amablemente que te indique qué desea modificar.]"
                    elif btn_id == "pay_card":
                        # Process Tilopay link generation
                        last_order = db.query(models.Order).filter(models.Order.customer_id == wa_id).order_by(models.Order.id.desc()).first()
                        if last_order:
                            last_order.payment_method = "Tarjeta"
                            db.commit()
                            try:
                                link_url = await tilopay_service.generate_payment_link_for_order(last_order)
                                background_tasks.add_task(
                                    wa_service.send_message,
                                    wa_id,
                                    f"¡Excelente elección! Puedes realizar tu pago seguro con tarjeta aquí: {link_url}"
                                )
                                content = f"[BOTÓN CLICK: {btn_title}]\n[SYSTEM INSTRUCTION: El sistema HA GENERADO AUTOMÁTICAMENTE el link de pago y se lo ha enviado al cliente. Confírmale al cliente que proceda al pago mediante el link y que aguardas notificación automática.]"
                            except Exception as e:
                                logger.error(f"Tilopay link generation error: {e}")
                                content = f"[BOTÓN CLICK: {btn_title}]\n[SYSTEM INSTRUCTION: Ocurrió un error interno generando el link de pago. Por favor indícale al cliente que intente otro método de pago o pida ayuda a gerencia.]"
                        else:
                            content = f"[BOTÓN CLICK: {btn_title}]\n[SYSTEM INSTRUCTION: El sistema intentó generar un link de pago pero no encontró ninguna orden. Pregúntale al cliente si aún desea realizar el pedido.]"

                    elif btn_id == "pay_sinpe":
                        last_order = db.query(models.Order).filter(models.Order.customer_id == wa_id).order_by(models.Order.id.desc()).first()
                        if last_order:
                            last_order.payment_method = "Sinpe Movil"
                            if customer:
                                customer.pending_receipt_for_order_id = last_order.id
                                from datetime import datetime
                                customer.pending_receipt_ts = datetime.utcnow()
                            db.commit()
                        content = f"[BOTÓN CLICK: {btn_title}]\n[SYSTEM INSTRUCTION: El cliente eligió Pagar por SINPE MÓVIL. El sistema ya preparó la orden para recibir comprobantes. Indícale el número de SINPE de la empresa (ej: 8888-8888 a nombre de Huevos CR o Carlos Perez) y pídele que envíe una captura del comprobante.]"
                        
                    elif btn_id == "pay_cash":
                        last_order = db.query(models.Order).filter(models.Order.customer_id == wa_id).order_by(models.Order.id.desc()).first()
                        if last_order:
                            last_order.payment_method = "Efectivo"
                            db.commit()
                        content = f"[BOTÓN CLICK: {btn_title}]\n[SYSTEM INSTRUCTION: El cliente eligió Pagar en EFECTIVO. Agradécele su elección e infórmale que pagará contra entrega.]"
                    else:
                        content = f"[BOTÓN CLICK: {btn_title}]"
                else:
                    content = f"[{msg_type.upper()}: {interactive_type}]"
            except Exception as e:
                logger.error(f"Error parsing interactive msg: {e}")
                content = f"[{msg_type.upper()} message]"

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
        
        if customer and media_url:
            # Primary check: explicit pending receipt flag (set when customer clicks Sinpe button)
            order_id_to_use = customer.pending_receipt_for_order_id

            # Fallback: if no flag set, look for the most recent Pendiente order (ANY payment method).
            # This covers cases where customer switches Tarjeta→Sinpe via text (n8n says "updated"
            # but doesn't actually call our API, so payment_method stays "Tarjeta" in DB).
            if not order_id_to_use:
                fallback_order = (
                    db.query(models.Order)
                    .filter(
                        models.Order.customer_id == wa_id,
                        models.Order.status == "Pendiente",
                    )
                    .order_by(models.Order.id.desc())
                    .first()
                )
                if fallback_order:
                    order_id_to_use = fallback_order.id
                    # Also update payment_method to Sinpe since customer is sending a receipt
                    fallback_order.payment_method = "Sinpe Movil"
                    db.commit()
                    logger.info(f"Receipt fallback: using latest Pendiente order #{order_id_to_use}, updated payment_method to Sinpe Movil")

            if order_id_to_use:
                # --- Auto-confirm receipt directly in Python ---
                target_order = db.query(models.Order).filter(models.Order.id == order_id_to_use).first()
                if target_order:
                    target_order.receipt_media_id = media_url
                    target_order.has_attachment = True
                    target_order.status = "payment_pending_validation"
                    customer.pending_receipt_media_id = None
                    customer.pending_receipt_for_order_id = None
                    customer.pending_receipt_ts = None
                    db.commit()
                    logger.info(f"Receipt auto-confirmed for Order #{order_id_to_use}")

                    # Send a thank-you message directly via WhatsApp (skip n8n for this)
                    background_tasks.add_task(
                        wa_service.send_message,
                        wa_id,
                        f"¡Gracias, {name.split()[0] if name else 'cliente'}! 🙏 Hemos recibido tu comprobante de pago para el Pedido #{order_id_to_use}. Lo validaremos en breve y te avisaremos cuando esté todo listo. ¡Pura vida! 🥚"
                    )

                is_receipt_candidate = True
                pending_order_id = order_id_to_use
                logger.info(f"Receipt Candidate Detected for Order {pending_order_id}")

        # Add flags to msg_data for n8n
        msg_data["is_receipt_candidate"] = is_receipt_candidate
        msg_data["pending_order_id"] = pending_order_id

        # 4. Trigger n8n (only for incoming user messages)
        # Skip n8n for receipt images — already handled above with direct reply
        if is_receipt_candidate:
            logger.info(f"Skipping n8n for receipt image (Order #{pending_order_id})")
        elif getattr(customer, "ai_active", True):
            background_tasks.add_task(forward_to_n8n, msg_data, db)
        else:
            logger.info(f"AI is OFF for {wa_id}. Message saved to context but not forwarded to n8n.")

        return {"status": "processed"}
    
    except Exception as e:
        import traceback
        logger.error(f"ERROR PROCESSING WEBHOOK: {str(e)}", exc_info=True)
        # Return 200 to Meta to avoid retry loops, but log heavily
        return {"status": "error", "detail": "Webhook internal error"}

@router.post("/n8n/send")
async def n8n_proxy_send(
    payload: dict = Body(...),
    db: Session = Depends(database.get_db)
):
    """
    Túnel especial para que n8n pase sus mensajes por Python antes de ir a WhatsApp.
    Permite inyectar botones interactivos si se detectan palabras mágicas.
    """
    wa_service = WhatsAppService()
    to = payload.get("to")
    body = payload.get("body", "")
    
    if not to or not body:
        return {"status": "error", "detail": "Missing 'to' or 'body'"}
        
    try:
        if "[BOTONES_CONFIRMAR]" in body:
            clean_text = body.replace("[BOTONES_CONFIRMAR]", "").strip()
            buttons = [
                {"id": "confirm_order_yes", "title": "✅ Sí, confirmar"},
                {"id": "confirm_order_no", "title": "❌ Modificar pedido"}
            ]
            await wa_service.send_interactive_buttons(to, clean_text, buttons)
        elif "[BOTONES_PAGO]" in body:
            clean_text = body.replace("[BOTONES_PAGO]", "").strip()
            buttons = [
                {"id": "pay_sinpe", "title": "📱 Sinpe Móvil"},
                {"id": "pay_card", "title": "💳 Tarjeta"},
                {"id": "pay_cash", "title": "💵 Efectivo"}
            ]
            await wa_service.send_interactive_buttons(to, clean_text, buttons)
        else:
            await wa_service.send_message(to, body)
            
        return {"status": "sent"}
    except Exception as e:
        import traceback
        logger.error(f"n8n proxy error: {str(e)}", exc_info=True)
        return {"status": "error", "detail": str(e)}

@router.post("/tilopay")
async def tilopay_webhook_callback(request: Request, db: Session = Depends(database.get_db)):
    """
    Recibe notificaciones de éxito de pago desde Tilopay (Webhook).
    Tilopay llamará aquí cuando se complete un pago.
    """
    try:
        payload = await request.json()
        logger.info(f"TILOPAY WEBHOOK PAYLOAD: {json.dumps(payload)}")
        
        # Intentaremos extraer la 'reference' (ej. ORD-123)
        reference = payload.get("reference") or payload.get("Order") or str(payload)
        
        if "ORD-" in str(reference):
            try:
                # Extraemos el numero de la orden de "ORD-123"
                parts = str(reference).split("-")
                for p in parts:
                    if p.isdigit():
                        order_id = int(p)
                        order = db.query(models.Order).filter(models.Order.id == order_id).first()
                        if order:
                            order.status = "paid"
                            order.payment_method = "Tilopay"
                            db.commit()
                            
                            # Enviar mensaje de WhatsApp al cliente agradeciendo
                            customer = order.customer
                            if customer:
                                wa_service = WhatsAppService()
                                
                                # Format total correctly, accounting for potential None or non-float values gracefully
                                total_fmt = f"{float(order.total_amount):,.2f}" if order.total_amount else "0.00"
                                
                                resumen_msg = (
                                    f"✅ *¡Pago Confirmado!*\n\n"
                                    f"Hemos recibido tu pago exitosamente para la orden #{order.id}.\n\n"
                                    f"📦 *Resumen de tu pedido:*\n"
                                    f"• Cantidad: {order.quantity} cartón(es)\n"
                                    f"• Entrega programada: {order.delivery_day or 'Por definir'}\n"
                                    f"• Total pagado: ₡{total_fmt}\n\n"
                                    f"¡Gracias por elegir HuevosCR!"
                                )
                                await wa_service.send_message(customer.whatsapp_id, resumen_msg)
                                
                            logger.info(f"Tilopay Webhook: Orden #{order.id} pagada exitosamente.")
                        break
            except Exception as inner_e:
                logger.error(f"Error procesando order reference en Tilopay webhook: {inner_e}")
                
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error procesando Tilopay webhook json: {e}")
        return {"status": "error"}

