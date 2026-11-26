from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.crud import breach as crud_breach
from app.db.session import get_db
from app.schemas.schemas import BreachDetailOut, BreachSummaryOut, PaginatedBreaches

router = APIRouter(prefix="/breaches", tags=["breaches"])


@router.get("", response_model=PaginatedBreaches)
def list_breaches(
    db: Session = Depends(get_db),
    country: str | None = Query(None, max_length=100),
    sector: str | None = Query(None, max_length=100),
    year: int | None = Query(None, ge=1990, le=2100),
    q: str | None = Query(None, max_length=200, description="Search by organization name"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> PaginatedBreaches:
    rows, total = crud_breach.list_breaches(
        db, country=country, sector=sector, year=year, q=q, limit=limit, offset=offset
    )
    return PaginatedBreaches(
        total=total,
        limit=limit,
        offset=offset,
        items=[BreachSummaryOut.model_validate(r) for r in rows],
    )


@router.get("/{slug}", response_model=BreachDetailOut)
def get_breach(slug: str, db: Session = Depends(get_db)) -> BreachDetailOut:
    breach = crud_breach.get_published_breach(db, slug)
    if breach is None:
        raise HTTPException(status_code=404, detail="Breach not found")
    return BreachDetailOut.model_validate(breach)
