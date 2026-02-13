import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Huevos CR"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./huevoscr.db")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "secret")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    
    # WhatsApp
    WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN")
    WHATSAPP_TOKEN: str = os.getenv("WHATSAPP_TOKEN")
    WHATSAPP_PHONE_ID: str = os.getenv("WHATSAPP_PHONE_ID")
    WHATSAPP_APP_ID: str = os.getenv("WHATSAPP_APP_ID")
    WHATSAPP_APP_SECRET: str = os.getenv("WHATSAPP_APP_SECRET")
    WHATSAPP_ACCOUNT_ID: str = os.getenv("WHATSAPP_ACCOUNT_ID")
    
    # n8n
    N8N_WEBHOOK_URL: str = os.getenv("N8N_WEBHOOK_URL")

settings = Settings()
