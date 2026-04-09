from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

load_dotenv()

from .database import engine, Base
from .api import auth, customers, config, sales, users, conversations, webhook, messaging
from .routers import pages, marketing

# Create tables (Moved to scripts to avoid Gunicorn worker collision)
# Base.metadata.create_all(bind=engine)


app = FastAPI(title="Huevos CR")

# CORS Settings
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://huevoscr.com",
    "https://www.huevoscr.com",
    "https://admin.huevoscr.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler
import logging
import traceback
logger = logging.getLogger(__name__)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unmet system exception at {request.url}: {exc}\\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Ha ocurrido un error interno en el servidor."},
    )


app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(config.router)
app.include_router(sales.router)
app.include_router(users.router)
app.include_router(conversations.router)
app.include_router(webhook.router)
app.include_router(messaging.router)
app.include_router(pages.router)
app.include_router(marketing.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

@app.get("/")
async def read_root(request: Request):
    # Placeholder for landing page
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt():
    content = """User-agent: *
Disallow: /admin/
Disallow: /seller/
Disallow: /login
Allow: /

Sitemap: https://www.huevoscr.com/sitemap.xml
"""
    return content

@app.get("/sitemap.xml")
def sitemap():
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://www.huevoscr.com/</loc>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://www.huevoscr.com/privacy-policy</loc>
    <changefreq>monthly</changefreq>
    <priority>0.5</priority>
  </url>
  <url>
    <loc>https://www.huevoscr.com/terms-of-service</loc>
    <changefreq>monthly</changefreq>
    <priority>0.5</priority>
  </url>
</urlset>"""
    return Response(content=content, media_type="application/xml")

@app.get("/privacy-policy")
async def privacy_policy(request: Request):
    return templates.TemplateResponse("privacy_policy.html", {"request": request})

@app.get("/terms-of-service")
async def terms_of_service(request: Request):
    return templates.TemplateResponse("terms_of_service.html", {"request": request})
