"""Ingestion pipeline: discover → extract → dedup → create review-queue candidates.

Every candidate is created as `in_review` with full provenance, a changelog entry, and an
audit entry. Nothing is published automatically — a human reviewer decides (Phase 3).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.core.slug import slugify, unique_breach_slug
from app.crud.audit import write_audit
from app.ingestion.connectors.base import Connector, Fetch
from app.ingestion.dedup import find_duplicate
from app.ingestion.extractor import ExtractedBreach, Extractor, RuleBasedExtractor
from app.models import Breach, ChangeLog, Provenance, Source
from app.models.enums import (
    ConfidenceLabel,
    ConfirmationStatus,
    ReviewStatus,
    RootCauseStatus,
    SourceType,
)

# Field-level provenance for a fresh EDGAR candidate.
_PROVENANCE = (
    ("organization", ConfidenceLabel.confirmed),
    ("date_disclosed", ConfidenceLabel.confirmed),
    ("country", ConfidenceLabel.analysis),
    ("root_cause_status", ConfidenceLabel.undisclosed),
)


def _create_candidate(db: Session, connector_name: str, ext: ExtractedBreach) -> Breach:
    slug = unique_breach_slug(db, f"{slugify(ext.organization)}-{ext.date_disclosed.year}")
    breach = Breach(
        slug=slug,
        organization=ext.organization,
        country="United States",  # SEC registrant default; refined during review
        sector="Unknown",
        date_disclosed=ext.date_disclosed,
        confirmation_status=ConfirmationStatus.confirmed,  # an official 8-K disclosure
        root_cause_status=RootCauseStatus.undisclosed,  # 8-Ks rarely state root cause
        review_status=ReviewStatus.in_review,
        is_published=False,
    )
    breach.sources.append(
        Source(
            url=ext.source_url,
            title=ext.source_title,
            publisher="SEC EDGAR",
            source_type=SourceType.filing,
            date_retrieved=date.today(),
        )
    )
    breach.changelog.append(
        ChangeLog(
            changed_by=f"ingestion:{connector_name}",
            change_type="ingested",
            reason="Candidate from SEC EDGAR 8-K Item 1.05 full-text search.",
        )
    )
    db.add(breach)
    db.flush()  # assign breach.id for provenance rows

    for field_name, label in _PROVENANCE:
        db.add(
            Provenance(
                entity="breach",
                entity_id=breach.id,
                field_name=field_name,
                confidence_label=label,
                date_retrieved=date.today(),
            )
        )
    write_audit(
        db,
        actor=None,
        action="breach.ingested",
        target_type="breach",
        target_id=slug,
        detail=f"connector={connector_name}",
        commit=False,
    )
    return breach


def ingest(
    db: Session, connector: Connector, fetch: Fetch, extractor: Extractor | None = None
) -> dict[str, int]:
    extractor = extractor or RuleBasedExtractor()
    raws = connector.discover(fetch)

    created = skipped = unparsed = 0
    for raw in raws:
        ext = extractor.extract(raw)
        if ext is None:
            unparsed += 1
            continue
        if find_duplicate(db, ext.organization, ext.date_disclosed) is not None:
            skipped += 1
            continue
        _create_candidate(db, connector.name, ext)
        created += 1

    db.commit()
    return {"discovered": len(raws), "created": created, "skipped": skipped, "unparsed": unparsed}
