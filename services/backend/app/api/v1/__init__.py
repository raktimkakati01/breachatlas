"""Version 1 API router aggregation."""

from fastapi import APIRouter

from app.api.v1 import breaches, controls, health, stats

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(breaches.router)
api_router.include_router(controls.router)
api_router.include_router(stats.router)
