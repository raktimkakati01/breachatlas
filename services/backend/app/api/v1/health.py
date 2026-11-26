from fastapi import APIRouter

from app.core.config import settings
from app.schemas.schemas import HealthOut

router = APIRouter(tags=["meta"])


@router.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut(status="ok", env=settings.APP_ENV)
