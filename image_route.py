"""Recognize *exact* previously distributed synthetic label-image files.

This is test-fixture selection, NOT OCR or product recognition. Only byte-for-byte
SHA-256 matches of the four published synthetic examples are accepted. All other
uploads must use OCR and human review or manual entry.
"""
from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

SAMPLE_SHA256_TO_KEY = {
    "4a02a746864d3b85f65041aed7fe7dda65f76e14cee596c6d0fb22d59d787af4": "match",
    "ce6ced419ba9efeb673f8872e426d157a503084ffbf38bd7cba400d422bd892c": "discrepancy",
    "642b32053fbcf15f3eab36a4c42c164bc762a40b52e87d1264b20e4b2283b2c3": "inconclusive",
    "e4d0848eafb4f4d8b2e7fefece6bdc6a409e086c9a9fad38facb09494a5d1193": "no_reference",
}

def identify_synthetic_sample(upload_bytes: bytes, scenarios: Sequence[Mapping[str, Any]]):
    """Return an existing fixture scenario or None. Never guess by filename."""
    digest = hashlib.sha256(upload_bytes).hexdigest()
    key = SAMPLE_SHA256_TO_KEY.get(digest)
    if key is None:
        return None
    return next((s for s in scenarios if s.get("key") == key), None)


def sample_label_values(upload_bytes: bytes, scenarios, fields):
    """Return (label, fixture) for exact sample; unknown files return blanks."""
    fixture = identify_synthetic_sample(upload_bytes, scenarios)
    if fixture is None:
        return {field: "" for field in fields}, None
    source = fixture.get("label", {})
    return {field: str(source.get(field, "")) for field in fields}, fixture
