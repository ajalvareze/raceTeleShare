"""Server-side rendered HTML pages."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
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


# /laps redirects to /sessions for backward compatibility
@router.get("/laps", response_class=HTMLResponse)
def laps_redirect():
    return RedirectResponse(url="/sessions", status_code=301)


@router.get("/laps/{lap_id}", response_class=HTMLResponse)
def lap_detail_page(lap_id: int, request: Request):
    return templates.TemplateResponse("laps/detail.html", {"request": request, "lap_id": lap_id})


@router.get("/compare", response_class=HTMLResponse)
def compare_page(request: Request):
    return templates.TemplateResponse("laps/compare.html", {"request": request})


@router.get("/sessions", response_class=HTMLResponse)
def sessions_page(request: Request):
    return templates.TemplateResponse("sessions/list.html", {"request": request})


@router.get("/sessions/{session_id}", response_class=HTMLResponse)
def session_detail_page(session_id: int, request: Request):
    return templates.TemplateResponse("sessions/detail.html", {"request": request, "session_id": session_id})


@router.get("/cars", response_class=HTMLResponse)
def cars_page(request: Request):
    return templates.TemplateResponse("cars/list.html", {"request": request})


@router.get("/tracks", response_class=HTMLResponse)
def tracks_page(request: Request):
    return templates.TemplateResponse("tracks/list.html", {"request": request})


@router.get("/tracks/{track_id}", response_class=HTMLResponse)
def track_detail_page(track_id: int, request: Request):
    return templates.TemplateResponse("tracks/detail.html", {"request": request, "track_id": track_id})


@router.get("/leaderboard/{config_id}", response_class=HTMLResponse)
def leaderboard_page(config_id: int, request: Request):
    return templates.TemplateResponse("tracks/leaderboard.html", {"request": request, "config_id": config_id})


@router.get("/events", response_class=HTMLResponse)
def events_page(request: Request):
    return templates.TemplateResponse("events/list.html", {"request": request})


@router.get("/events/{event_id}", response_class=HTMLResponse)
def event_detail_page(event_id: int, request: Request):
    return templates.TemplateResponse("events/detail.html", {"request": request, "event_id": event_id})


@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse("admin/dashboard.html", {"request": request})
