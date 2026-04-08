import httpx
import re
import os
from typing import List, Dict, Any

def format_whatsapp_number(number: str, default_country_code: str = "506") -> str:
    """
    Limpia un número de teléfono y asegura que tenga formato internacional.
    """
    if not number:
        return ""
    
    # Remover todo lo que no sea dígito
    clean_number = re.sub(r'\D', '', str(number))
    
    # Si el número resultante tiene 8 dígitos (formato local típico de Costa Rica), agregar el código
    if len(clean_number) == 8:
        return f"{default_country_code}{clean_number}"
        
    # Si ya empieza con el código de país (ej. 50688888888 u otros internacionales), devolverlo tal cual
    return clean_number

async def fetch_meta_templates(waba_id: str, access_token: str) -> List[Dict[Any, Any]]:
    """
    Obtiene las plantillas aprobadas desde Meta Graph API.
    """
    url = f"https://graph.facebook.com/v20.0/{waba_id}/message_templates"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])

async def send_meta_template(
    phone_number_id: str, 
    access_token: str, 
    to_number: str, 
    template_name: str, 
    language_code: str, 
    components: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Envía un mensaje de plantilla usando Meta Graph API.
    """
    url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    formatted_to = format_whatsapp_number(to_number)
    
    payload = {
        "messaging_product": "whatsapp",
        "to": formatted_to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {
                "code": language_code
            },
            "components": components
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
