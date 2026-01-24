from fastapi import APIRouter, File, UploadFile
import os
import uuid
import shutil

router = APIRouter(
    tags=["Uploads"]
)

@router.post("/upload")
async def upload_receipt(file: UploadFile = File(...)):
    # Crear carpeta si no existe
    upload_dir = "app/static/receipts"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generar nombre único
    file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = f"{upload_dir}/{unique_filename}"
    
    # Guardar archivo
    with open(file_path, "wb") as f:
        # Read content from UploadFile
        content = await file.read()
        f.write(content)
    
    # Devolver URL pública
    # NOTE: Assuming the server is accessed via a tunnel or specific domain.
    # The user can prepend their domain if needed, but returning the relative path
    # and letting the client handle the domain is often safer, OR returning a full URL if domain is known.
    # The user example showed "https://tudominio.com/...", for now we return the relative path 
    # and the full path logic can be handled by the client or configured here.
    # However, to be helpful, let's return the relative path which works with the existing modal logic if mapped correctly,
    # OR construct a full URL if we had the request context. 
    # Given the user request: "public_url = f'https://tudominio.com/static/receipts/{unique_filename}'"
    # I will verify how to get the domain or just return the static path which works if relative.
    
    # Using relative path for maximum flexibility (browser resolves it against current origin)
    # BUT n8n needs a full URL to pass to the API? No, n8n passes the URL to the PUT endpoint.
    # The PUT endpoint saves it as string. The browser displays it.
    # If I save "/static/receipts/..." it works in browser.
    
    public_path = f"/static/receipts/{unique_filename}"
    
    # Constructing a full URL would require knowing the tunnel URL dynamically or env var.
    # For now, returning the relative path is safest and usually robust for web apps.
    
    return {
        "success": True,
        "url": public_path,
        "filename": unique_filename
    }
