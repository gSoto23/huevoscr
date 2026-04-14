import httpx
from datetime import datetime, timedelta
from ..core import config
import logging

logger = logging.getLogger(__name__)

# Cache del token en memoria
_cached_token = None
_token_expiry = None

async def get_tilopay_token() -> str:
    global _cached_token, _token_expiry
    
    # Si tenemos un token válido (con al menos 10 min de sobra), lo usamos
    if _cached_token and _token_expiry:
        if datetime.now() < (_token_expiry - timedelta(minutes=10)):
            return _cached_token

    if not config.settings.TILOPAY_API_USER or not config.settings.TILOPAY_API_PASSWORD:
        raise ValueError("Credenciales de Tilopay no configuradas en el sistema.")

    login_url = "https://app.tilopay.com/api/v1/login"
    login_payload = {
        "apiuser": config.settings.TILOPAY_API_USER,
        "password": config.settings.TILOPAY_API_PASSWORD
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(login_url, json=login_payload, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            
            _cached_token = data.get("access_token")
            expires_in = data.get("expires_in", 86400) # Segundos
            _token_expiry = datetime.now() + timedelta(seconds=expires_in)
            
            return _cached_token
        except Exception as e:
            logger.error(f"Error autenticando con Tilopay: {e}")
            raise

async def generate_payment_link_for_order(order) -> str:
    """
    Genera un link de pago en Tilopay para la orden dada.
    """
    token = await get_tilopay_token()
    
    link_url = "https://app.tilopay.com/api/v1/createLinkPayment"
    
    # URL al que Tilopay hara el POST cuando el pago sea exitoso
    webhook_url = f"{config.settings.APP_BASE_URL.rstrip('/')}/webhook/tilopay"
    
    link_payload = {
        "key": config.settings.TILOPAY_KEY,
        "amount": str(float(order.total_amount or 0)),
        "currency": "CRC", # O la moneda pertinente
        "reference": f"ORD-{order.id}",
        "type": 0,
        "description": f"Pago de Orden #{order.id} - HuevosCR",
        "client": order.customer.name if order.customer else "Cliente HuevosCR",
        "callback_url": f"{config.settings.APP_BASE_URL.rstrip('/')}",
        "webhook_url": webhook_url
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(link_url, json=link_payload, headers=headers, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()
            # Tilopay responde en "url" si es exitoso
            return data.get("url")
        except Exception as e:
            logger.error(f"Error generando link de Tilopay para Orden {order.id}: {e}\nPayload enviado: {link_payload}")
            if isinstance(e, httpx.HTTPStatusError):
                logger.error(f"Detalle API: {e.response.text}")
            raise
