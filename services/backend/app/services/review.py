"""The review workflow state machine.

Nothing publishes automatically: `is_published` only becomes true on an explicit `publish`
transition, which requires the record to already be `approved`. Every transition writes both
a per-breach changelog entry and an audit-log entry.
"""

from __future__ import annotations

from app.crud.audit import write_audit
from app.models import Breach, ChangeLog, User
from app.models.enums import ReviewStatus

# action -> (allowed source states, target state)
_TRANSITIONS: dict[str, tuple[set[ReviewStatus], ReviewStatus]] = {
    "submit": ({ReviewStatus.draft, ReviewStatus.changes_requested}, ReviewStatus.in_review),
    "request_changes": ({ReviewStatus.in_review}, ReviewStatus.changes_requested),
    "approve": ({ReviewStatus.in_review}, ReviewStatus.approved),
    "publish": ({ReviewStatus.approved}, ReviewStatus.published),
    "reject": (
        {ReviewStatus.in_review, ReviewStatus.changes_requested, ReviewStatus.approved},
        ReviewStatus.rejected,
    ),
}


class TransitionError(Exception):
    """Raised when a review transition is not allowed from the current state."""


def allowed_actions(status: ReviewStatus) -> list[str]:
    return [a for a, (sources, _) in _TRANSITIONS.items() if status in sources]


def apply_transition(
    db,
    breach: Breach,
    action: str,
    *,
    actor: User,
    ip: str | None = None,
    reason: str | None = None,
) -> Breach:
    if action not in _TRANSITIONS:
        raise TransitionError(f"Unknown action: {action}")

    sources, target = _TRANSITIONS[action]
    if breach.review_status not in sources:
        raise TransitionError(f"Cannot {action} a breach in state '{breach.review_status.value}'.")

    old = breach.review_status
    breach.review_status = target
    if target is ReviewStatus.published:
        breach.is_published = True

    breach.changelog.append(
        ChangeLog(
            changed_by=actor.email,
            change_type="transition",
            field="review_status",
            old_value=old.value,
            new_value=target.value,
            reason=reason,
        )
    )
    write_audit(
        db,
        actor=actor,
        action=f"breach.{action}",
        target_type="breach",
        target_id=breach.slug,
        ip=ip,
        detail=reason,
        commit=False,
    )
    db.commit()
    db.refresh(breach)
    return breach
