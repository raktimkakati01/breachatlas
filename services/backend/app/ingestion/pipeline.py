"""Ingestion pipeline: discover → extract → dedup → create review-queue candidates.

Source-agnostic: each connector supplies its own extractor. Every candidate is created as
`in_review` with per-field provenance, a changelog entry, and an audit entry. Nothing is
published automatically — a human reviewer decides (Phase 3).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.core.slug import slugify, unique_breach_slug
from app.crud.audit import write_audit
from app.ingestion.connectors.base import Connector, Fetch
from app.ingestion.dedup import find_duplicate
from app.ingestion.extractor import ExtractedBreach, Extractor
from app.models import Breach, ChangeLog, Provenance, Source
from app.models.enums import ConfidenceLabel, ReviewStatus, RootCauseStatus


def _create_candidate(db: Session, connector_name: str, ext: ExtractedBreach) -> Breach:
    slug = unique_breach_slug(db, f"{slugify(ext.organization)}-{ext.date_disclosed.year}")
    breach = Breach(
        slug=slug,
        organization=ext.organization,
        country=ext.country,
        sector=ext.sector or "Unknown",
        date_disclosed=ext.date_disclosed,
        records_affected=ext.records_affected,
        confirmation_status=ext.confirmation_status,
        root_cause_status=RootCauseStatus.undisclosed,  # never guessed from ingestion
        review_status=ReviewStatus.in_review,
        is_published=False,
    )
    breach.sources.append(
        Source(
            url=ext.source_url,
            title=ext.source_title,
            publisher=ext.source_publisher,
            source_type=ext.source_type,
            date_retrieved=date.today(),
        )
    )
    breach.changelog.append(
        ChangeLog(
            changed_by=f"ingestion:{connector_name}",
            change_type="ingested",
            reason=f"Candidate ingested from {ext.source_publisher}.",
        )
    )
    db.add(breach)
    db.flush()  # assign breach.id for provenance

    provenance = {
        "organization": ConfidenceLabel.confirmed,
        "date_disclosed": ConfidenceLabel.confirmed,
        "country": ConfidenceLabel.analysis,
        "root_cause_status": ConfidenceLabel.undisclosed,
        "records_affected": (
            ConfidenceLabel.confirmed
            if "records_affected" in ext.confident_fields
            else ConfidenceLabel.undisclosed
        ),
    }
    for field_name, label in provenance.items():
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
    extractor = extractor or connector.extractor
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
