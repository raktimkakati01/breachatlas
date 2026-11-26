from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.crud import control as crud_control
from app.db.session import get_db
from app.schemas.schemas import BreachSummaryOut, ControlOut, ControlPageOut

router = APIRouter(prefix="/controls", tags=["controls"])


@router.get("", response_model=list[ControlOut])
def list_controls(db: Session = Depends(get_db)) -> list[ControlOut]:
    return [ControlOut.model_validate(c) for c in crud_control.list_controls(db)]


@router.get("/{slug}", response_model=ControlPageOut)
def control_page(
    slug: str,
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> ControlPageOut:
    result = crud_control.get_control_page(db, slug, limit=limit, offset=offset)
    if result is None:
        raise HTTPException(status_code=404, detail="Control not found")
    control, breaches, total = result
    return ControlPageOut(
        control=ControlOut.model_validate(control),
        breach_count=total,
        breaches=[BreachSummaryOut.model_validate(b) for b in breaches],
    )
