"""Admin API router (mounted under /admin). Requires authentication + roles."""

from fastapi import APIRouter

from app.api.admin import audit, auth, review, users

admin_router = APIRouter()
admin_router.include_router(auth.router)
admin_router.include_router(users.router)
admin_router.include_router(review.router)
admin_router.include_router(audit.router)
