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
    # Tilopay
    TILOPAY_API_USER: str = os.getenv("TILOPAY_API_USER")
    TILOPAY_API_PASSWORD: str = os.getenv("TILOPAY_API_PASSWORD")
    TILOPAY_KEY: str = os.getenv("TILOPAY_KEY")
    APP_BASE_URL: str = os.getenv("APP_BASE_URL", "https://admin.huevoscr.com") # Usado para el webhook
    
    # SendGrid / SMTP config
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_SENDER: str = os.getenv("SMTP_SENDER", "hola@huevoscr.com")

settings = Settings()
