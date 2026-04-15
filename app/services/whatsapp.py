import httpx
import os
import json
import logging
from ..core import config  # Assuming you might have a config module, otherwise os.getenv

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.api_token = os.getenv("WHATSAPP_TOKEN")
        self.phone_id = os.getenv("WHATSAPP_PHONE_ID")
        self.api_version = "v18.0" # Or latest
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    async def send_message(self, to: str, body: str):
        """
        Sends a text message using the WhatsApp Graph API.
        """
        url = f"{self.base_url}/{self.phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body}
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def send_template(self, to: str, template_name: str, language_code: str = "es"):
        """
        Sends a template message (e.g., for starting 24h window if needed, though usually replies are free-form if within window).
        """
        url = f"{self.base_url}/{self.phone_id}/messages"
        headers = {
             "Authorization": f"Bearer {self.api_token}",
             "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def get_media_url(self, media_id: str) -> str:
        """
        Retrieves the temporary download URL for a media object using its ID.
        """
        url = f"{self.base_url}/{media_id}"
        headers = {
            "Authorization": f"Bearer {self.api_token}"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                media_url = data.get("url")
                if not media_url:
                    logger.error(f"get_media_url: API returned no URL for media_id={media_id}. Response: {data}")
                return media_url
            except Exception as e:
                logger.error(f"get_media_url error for media_id={media_id}: {e}", exc_info=True)
                return None

    async def upload_media(self, file_bytes: bytes, mime_type: str) -> str:
        url = f"{self.base_url}/{self.phone_id}/media"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
        }
        files = {
            "file": ("uploaded_file", file_bytes, mime_type)
        }
        data = {
            "messaging_product": "whatsapp"
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, data=data, files=files)
            response.raise_for_status()
            data = response.json()
            return data.get("id")

    async def send_media(self, to: str, media_id: str, media_type: str = "image", caption: str = ""):
        url = f"{self.base_url}/{self.phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": media_type,
            media_type: {"id": media_id}
        }
        if caption and media_type in ["image", "video", "document"]:
            payload[media_type]["caption"] = caption

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def send_interactive_buttons(self, to: str, text: str, buttons: list):
        url = f"{self.base_url}/{self.phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        formatted_buttons = []
        for btn in buttons[:3]:
             formatted_buttons.append({
                  "type": "reply",
                  "reply": {
                       "id": btn["id"],
                       "title": btn["title"]
                  }
             })

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": text
                },
                "action": {
                    "buttons": formatted_buttons
                }
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
