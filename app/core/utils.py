import httpx
import os
import uuid
import logging
import boto3
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

async def download_whatsapp_image(media_url: str, folder: str = "receipts") -> str:
    """
    Downloads media from a WhatsApp URL using the WHATSAPP_TOKEN.
    Saves it to app/static/{folder} and returns the local relative path.
    If download fails, returns the original URL.
    """
    token = os.getenv("WHATSAPP_TOKEN")
    if not token:
        logger.warning("WHATSAPP_TOKEN not set. Skipping download.")
        return media_url

    try:
        # Create directory if not exists
        upload_dir = Path(f"app/static/{folder}")
        upload_dir.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(media_url, headers=headers, timeout=30.0)

            if response.status_code == 200:
                import mimetypes
                content_type = response.headers.get("Content-Type", "")
                ext = mimetypes.guess_extension(content_type)
                if not ext:
                    if "image" in content_type: ext = ".jpg"
                    elif "audio" in content_type: ext = ".ogg"
                    elif "video" in content_type: ext = ".mp4"
                    elif "pdf" in content_type: ext = ".pdf"
                    else: ext = ".bin"
                
                filename = f"{uuid.uuid4()}{ext}"

                bucket_name = os.getenv("AWS_BUCKET_NAME")
                
                if bucket_name:
                    # Modo Producción S3: Subir bytes directamente a S3 sin guardar en disco
                    s3_path = f"public/{folder}/{filename}"
                    s3_client = boto3.client('s3')
                    s3_client.put_object(
                        Bucket=bucket_name,
                        Key=s3_path,
                        Body=response.content,
                        ContentType=content_type,
                        # Usar predeterminado de IAM Roles/Keys y setear a lectura publica si se requiere
                    )
                    
                    # Devolver la URL absoluta del bucket S3
                    s3_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_path}"
                    logger.info(f"Uploaded WhatsApp media to S3: {s3_url}")
                    return s3_url

                else:
                    # Modo Local / Desarrollo: Guardar en disco duro
                    file_path = upload_dir / filename
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                    
                    logger.info(f"Downloaded WhatsApp media locally to {file_path}")
                    return f"/static/{folder}/{filename}"
            else:
                logger.error(f"Failed to download media. Status: {response.status_code}, URL: {media_url}")
                return media_url

    except Exception as e:
        logger.error(f"Error downloading WhatsApp media: {str(e)}", exc_info=True)
        return media_url
