"""The admin review queue and workflow transitions.

Role model:
  * editor   — create/edit drafts, submit to review
  * reviewer — request changes, approve, publish, reject (plus everything an editor can do)
  * admin    — everything
Nothing is published automatically; publishing requires an explicit reviewer/admin action.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, require_role
from app.core.slug import slugify, unique_breach_slug
from app.crud.audit import write_audit
from app.db.session import get_db
from app.models import Breach, ChangeLog, User
from app.models.enums import ConfirmationStatus, ReviewStatus, RootCauseStatus, UserRole
from app.schemas.admin import AdminBreachOut, BreachDraftCreateIn, TransitionIn
from app.services.review import TransitionError, apply_transition

router = APIRouter(prefix="/breaches", tags=["admin:review"])

# Anyone in the admin area (editor and up) may read the queue.
_read_dep = require_role(UserRole.editor, UserRole.reviewer)
# Drafting is an editor action.
_edit_dep = require_role(UserRole.editor, UserRole.reviewer)
# Review decisions are reviewer actions.
_review_dep = require_role(UserRole.reviewer)


def _get_or_404(db: Session, slug: str) -> Breach:
    breach = db.scalar(select(Breach).where(Breach.slug == slug))
    if breach is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Breach not found")
    return breach


@router.get("", response_model=list[AdminBreachOut])
def queue(
    review_status: ReviewStatus | None = None,
    _user: User = Depends(_read_dep),
    db: Session = Depends(get_db),
) -> list[Breach]:
    stmt = select(Breach)
    if review_status is not None:
        stmt = stmt.where(Breach.review_status == review_status)
    return list(db.scalars(stmt.order_by(Breach.updated_at.desc())).all())


@router.get("/{slug}", response_model=AdminBreachOut)
def get_one(slug: str, _user: User = Depends(_read_dep), db: Session = Depends(get_db)) -> Breach:
    return _get_or_404(db, slug)


@router.post("", response_model=AdminBreachOut, status_code=status.HTTP_201_CREATED)
def create_draft(
    payload: BreachDraftCreateIn,
    request: Request,
    user: User = Depends(_edit_dep),
    db: Session = Depends(get_db),
) -> Breach:
    slug = unique_breach_slug(db, f"{slugify(payload.organization)}-{payload.date_disclosed.year}")
    breach = Breach(
        slug=slug,
        organization=payload.organization,
        country=payload.country,
        sector=payload.sector,
        date_disclosed=payload.date_disclosed,
        summary=payload.summary,
        confirmation_status=ConfirmationStatus.unconfirmed,
        root_cause_status=RootCauseStatus.undisclosed,
        review_status=ReviewStatus.draft,
        is_published=False,
    )
    breach.changelog.append(
        ChangeLog(
            changed_by=user.email, change_type="created", reason="Draft created in review queue."
        )
    )
    db.add(breach)
    db.flush()
    write_audit(
        db,
        actor=user,
        action="breach.create",
        target_type="breach",
        target_id=breach.slug,
        ip=get_client_ip(request),
        commit=False,
    )
    db.commit()
    db.refresh(breach)
    return breach


def _transition(
    slug: str, action: str, payload: TransitionIn, request: Request, user: User, db: Session
) -> Breach:
    breach = _get_or_404(db, slug)
    try:
        return apply_transition(
            db, breach, action, actor=user, ip=get_client_ip(request), reason=payload.reason
        )
    except TransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{slug}/submit", response_model=AdminBreachOut)
def submit(
    slug: str,
    request: Request,
    payload: TransitionIn | None = None,
    user: User = Depends(_edit_dep),
    db: Session = Depends(get_db),
) -> Breach:
    return _transition(slug, "submit", payload or TransitionIn(), request, user, db)


@router.post("/{slug}/request-changes", response_model=AdminBreachOut)
def request_changes(
    slug: str,
    request: Request,
    payload: TransitionIn | None = None,
    user: User = Depends(_review_dep),
    db: Session = Depends(get_db),
) -> Breach:
    return _transition(slug, "request_changes", payload or TransitionIn(), request, user, db)


@router.post("/{slug}/approve", response_model=AdminBreachOut)
def approve(
    slug: str,
    request: Request,
    payload: TransitionIn | None = None,
    user: User = Depends(_review_dep),
    db: Session = Depends(get_db),
) -> Breach:
    return _transition(slug, "approve", payload or TransitionIn(), request, user, db)


@router.post("/{slug}/publish", response_model=AdminBreachOut)
def publish(
    slug: str,
    request: Request,
    payload: TransitionIn | None = None,
    user: User = Depends(_review_dep),
    db: Session = Depends(get_db),
) -> Breach:
    return _transition(slug, "publish", payload or TransitionIn(), request, user, db)


@router.post("/{slug}/reject", response_model=AdminBreachOut)
def reject(
    slug: str,
    request: Request,
    payload: TransitionIn | None = None,
    user: User = Depends(_review_dep),
    db: Session = Depends(get_db),
) -> Breach:
    return _transition(slug, "reject", payload or TransitionIn(), request, user, db)
