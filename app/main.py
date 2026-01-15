from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .database import engine, Base
from .api import auth, customers, config, sales, users
from .routers import pages

# Create tables
Base.metadata.create_all(bind=engine)


app = FastAPI(title="Huevos CR")

app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(config.router)
app.include_router(sales.router)
app.include_router(users.router)
app.include_router(pages.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

@app.get("/")
async def read_root(request: Request):
    # Placeholder for landing page
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/health")
def health_check():
    return {"status": "ok"}
