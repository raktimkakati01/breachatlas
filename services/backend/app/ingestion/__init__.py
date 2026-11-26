"""Ingestion worker: source connectors, a pluggable extractor, dedup, and candidate creation.

Runs as its own container (separate command on the backend image). Candidates always land
in the review queue as `in_review` — nothing is published automatically.
"""
