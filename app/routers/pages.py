from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from .. import auth

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    return templates.TemplateResponse("admin/dashboard.html", {"request": request})

@router.get("/admin/customers", response_class=HTMLResponse)
async def admin_customers(request: Request):
    return templates.TemplateResponse("admin/customers.html", {"request": request})

@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request):
    return templates.TemplateResponse("admin/users.html", {"request": request})

@router.get("/admin/sales", response_class=HTMLResponse)
async def admin_sales(request: Request):
    return templates.TemplateResponse("admin/sales.html", {"request": request})

@router.get("/admin/config", response_class=HTMLResponse)
async def admin_config(request: Request):
    return templates.TemplateResponse("admin/config.html", {"request": request})

@router.get("/admin/support", response_class=HTMLResponse)
async def admin_support(request: Request):
    return templates.TemplateResponse("admin/support.html", {"request": request})

@router.get("/seller/dashboard", response_class=HTMLResponse)
async def seller_dashboard(request: Request):
    return templates.TemplateResponse("seller/dashboard.html", {"request": request})

@router.get("/seller/customers", response_class=HTMLResponse)
async def seller_customers(request: Request):
    return templates.TemplateResponse("seller/customers.html", {"request": request})

@router.get("/seller/sales", response_class=HTMLResponse)
async def seller_sales(request: Request):
    return templates.TemplateResponse("seller/sales.html", {"request": request})
