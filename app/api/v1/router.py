from fastapi import APIRouter
from app.api.v1 import auth, users, tracks, cars, sessions, laps, leaderboard, events, admin

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(tracks.router)
api_router.include_router(cars.router)
api_router.include_router(sessions.router)
api_router.include_router(laps.router)
api_router.include_router(leaderboard.router)
api_router.include_router(events.router)
api_router.include_router(admin.router)
