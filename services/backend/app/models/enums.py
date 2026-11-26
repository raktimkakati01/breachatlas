"""Controlled vocabularies for the data model.

These enums encode the project's non-negotiable labelling rules (see docs/decisions.md
ADR-0001 / ADR-0006): confirmation status, root-cause disclosure, and the per-field
provenance confidence label.
"""

from __future__ import annotations

import enum


class ConfirmationStatus(str, enum.Enum):
    confirmed = "confirmed"
    denied = "denied"
    unconfirmed = "unconfirmed"


class RootCauseStatus(str, enum.Enum):
    # Defaults to `undisclosed` — we never guess a root cause.
    disclosed = "disclosed"
    undisclosed = "undisclosed"


class AttackPhase(str, enum.Enum):
    initial_access = "initial_access"
    escalation_movement = "escalation_movement"
    exfiltration = "exfiltration"
    impact = "impact"


class ConfidenceLabel(str, enum.Enum):
    confirmed = "confirmed"  # official source
    reported = "reported"  # credible news
    analysis = "analysis"  # our own assessment
    undisclosed = "undisclosed"  # not stated by any source


class SourceType(str, enum.Enum):
    official = "official"  # the breached org's own disclosure
    regulator = "regulator"  # SEC, ICO, HHS OCR, state AG, etc.
    filing = "filing"  # a formal filing (e.g. SEC 8-K)
    news = "news"  # credible news reporting


class ControlRelationship(str, enum.Enum):
    would_have_prevented = "would_have_prevented"
    would_have_limited = "would_have_limited"


class UserRole(str, enum.Enum):
    editor = "editor"  # create/edit draft breaches, submit to review
    reviewer = "reviewer"  # review the queue: approve, request changes, publish
    admin = "admin"  # all of the above + user management + audit log


class ReviewStatus(str, enum.Enum):
    draft = "draft"
    in_review = "in_review"
    changes_requested = "changes_requested"
    approved = "approved"
    published = "published"
    rejected = "rejected"
