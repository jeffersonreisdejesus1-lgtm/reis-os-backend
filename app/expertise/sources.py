from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .registry import EXPERT_SOURCE_CLASS


@dataclass(frozen=True)
class ExpertSourceRecord:
    source_id: str
    author: str
    work: str
    edition_or_date: str
    source_type: str
    locator: str
    content_hash: str
    ingestion_version: str
    licensing_access_class: str
    retrieval_tags: tuple[str, ...]
    source_family: str = ""
    provenance_hash: str = ""
    source_class: str = EXPERT_SOURCE_CLASS

    def __post_init__(self) -> None:
        if not self.source_family:
            inferred = self.source_id.split("-", 1)[0].upper()
            object.__setattr__(self, "source_family", inferred)
        if not self.provenance_hash:
            object.__setattr__(self, "provenance_hash", source_record_digest(self))


@dataclass(frozen=True)
class ExpertEvidenceFragment:
    source_id: str
    fragment_id: str
    content: str
    locator: str
    content_hash: str
    retrieval_tags: tuple[str, ...]


def sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def source_record_digest(record: ExpertSourceRecord) -> str:
    payload = {
        "source_id": record.source_id,
        "source_family": record.source_family,
        "author": record.author,
        "work": record.work,
        "edition_or_date": record.edition_or_date,
        "source_type": record.source_type,
        "locator": record.locator,
        "ingestion_version": record.ingestion_version,
        "licensing_access_class": record.licensing_access_class,
        "retrieval_tags": list(record.retrieval_tags),
        "source_class": record.source_class,
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256_text(canonical)


def validate_source_record(record: ExpertSourceRecord) -> None:
    if record.source_class != EXPERT_SOURCE_CLASS:
        raise ValueError("expert_source_class_must_remain_external")
    required = (
        record.source_id,
        record.source_family,
        record.author,
        record.work,
        record.source_type,
        record.locator,
        record.content_hash,
        record.provenance_hash,
        record.ingestion_version,
        record.licensing_access_class,
    )
    if not all(value.strip() for value in required):
        raise ValueError("expert_source_provenance_incomplete")
    if len(record.content_hash) != 64:
        raise ValueError("expert_source_hash_invalid")
    if record.provenance_hash != source_record_digest(record):
        raise ValueError("expert_source_provenance_integrity_failure")


def validate_fragment(fragment: ExpertEvidenceFragment) -> None:
    if not fragment.source_id or not fragment.fragment_id or not fragment.locator:
        raise ValueError("expert_fragment_provenance_incomplete")
    if sha256_text(fragment.content) != fragment.content_hash:
        raise ValueError("expert_fragment_integrity_failure")
