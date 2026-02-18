"""Server-side rendered HTML pages."""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})


@router.get("/laps", response_class=HTMLResponse)
def laps_page(request: Request):
    return templates.TemplateResponse("laps/list.html", {"request": request})


@router.get("/laps/{lap_id}", response_class=HTMLResponse)
def lap_detail_page(lap_id: int, request: Request):
    return templates.TemplateResponse("laps/detail.html", {"request": request, "lap_id": lap_id})


@router.get("/compare", response_class=HTMLResponse)
def compare_page(request: Request):
    return templates.TemplateResponse("laps/compare.html", {"request": request})
