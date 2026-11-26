from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud import stats as crud_stats
from app.db.session import get_db
from app.schemas.schemas import StatsOut

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)) -> StatsOut:
    return crud_stats.get_stats(db)
