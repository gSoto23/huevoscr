import httpx
import os
import uuid
import logging
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

async def download_whatsapp_image(media_url: str) -> str:
    """
    Downloads media from a WhatsApp URL using the WHATSAPP_TOKEN.
    Saves it to app/static/receipts and returns the local relative path.
    If download fails, returns the original URL.
    """
    token = os.getenv("WHATSAPP_TOKEN")
    if not token:
        logger.warning("WHATSAPP_TOKEN not set. Skipping download.")
        return media_url

    try:
        # Create directory if not exists
        upload_dir = Path("app/static/receipts")
        upload_dir.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(media_url, headers=headers, timeout=30.0)

            if response.status_code == 200:
                # Determine extension (default to .jpg if unknown)
                content_type = response.headers.get("content-type", "")
                ext = ".jpg"
                if "image/png" in content_type:
                    ext = ".png"
                elif "image/jpeg" in content_type:
                    ext = ".jpg"
                elif "application/pdf" in content_type:
                    ext = ".pdf"
                
                filename = f"{uuid.uuid4()}{ext}"
                file_path = upload_dir / filename
                
                with open(file_path, "wb") as f:
                    f.write(response.content)
                
                logger.info(f"Downloaded WhatsApp media to {file_path}")
                return f"/static/receipts/{filename}"
            else:
                logger.error(f"Failed to download media. Status: {response.status_code}, URL: {media_url}")
                return media_url

    except Exception as e:
        logger.error(f"Error downloading WhatsApp media: {e}")
        return media_url
