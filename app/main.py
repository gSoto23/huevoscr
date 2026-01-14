from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .database import engine, Base

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Huevos CR")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

@app.get("/")
async def read_root(request: Request):
    # Placeholder for landing page
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/health")
def health_check():
    return {"status": "ok"}
