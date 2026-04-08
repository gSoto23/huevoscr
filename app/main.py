from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

load_dotenv()

from .database import engine, Base
from .api import auth, customers, config, sales, users, conversations, webhook, messaging
from .routers import pages, marketing

# Create tables
Base.metadata.create_all(bind=engine)


app = FastAPI(title="Huevos CR")

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

@app.get("/privacy-policy")
async def privacy_policy(request: Request):
    return templates.TemplateResponse("privacy_policy.html", {"request": request})

@app.get("/terms-of-service")
async def terms_of_service(request: Request):
    return templates.TemplateResponse("terms_of_service.html", {"request": request})
