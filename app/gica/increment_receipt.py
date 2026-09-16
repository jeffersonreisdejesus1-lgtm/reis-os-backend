from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .increment_evidence import (
    ActorReference,
    EvidenceReference,
    EvidenceValue,
    ExecutionEvidence,
)

SCHEMA_VERSION = "gica.increment-receipt/v1"
_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")


class FileChangeType:
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    RENAMED = "RENAMED"


@dataclass(frozen=True)
class FileChange:
    path: str
    change_type: str
    before_blob_sha: str | None = None
    after_blob_sha: str | None = None

    def validate(self) -> None:
        if not self.path or self.change_type not in {
            FileChangeType.ADDED,
            FileChangeType.MODIFIED,
            FileChangeType.DELETED,
            FileChangeType.RENAMED,
        }:
            raise ValueError("invalid_file_change")
        if self.before_blob_sha is not None and not _SHA_RE.fullmatch(
            self.before_blob_sha
        ):
            raise ValueError("invalid_before_blob_sha")
        if self.after_blob_sha is not None and not _SHA_RE.fullmatch(
            self.after_blob_sha
        ):
            raise ValueError("invalid_after_blob_sha")


@dataclass(frozen=True)
class Decision:
    value: str
    reason: str

    PASS = "PASS"
    HOLD = "HOLD"
    REPAIR = "REPAIR"

    def __post_init__(self) -> None:
        if self.value not in {self.PASS, self.HOLD, self.REPAIR}:
            raise ValueError("invalid_decision")


@dataclass(frozen=True)
class IncrementReceipt:
    schema_version: str
    receipt_id: str
    intention_id: str
    program: str
    repository: str
    branch: str
    head_before: EvidenceValue[str]
    head_after: EvidenceValue[str]
    files_changed: EvidenceValue[tuple[FileChange, ...]]
    test_commands: tuple[str, ...]
    test_result: ExecutionEvidence
    build_result: ExecutionEvidence
    runtime_result: ExecutionEvidence
    evidence_references: tuple[EvidenceReference, ...]
    decision: Decision
    created_at: str
    executor: ActorReference
    reviewer: ActorReference | None

    @staticmethod
    def canonical_payload(
        *,
        schema_version: str,
        intention_id: str,
        program: str,
        repository: str,
        branch: str,
        head_before: EvidenceValue[str],
        head_after: EvidenceValue[str],
    ) -> dict[str, Any]:
        def head(value: EvidenceValue[str]) -> dict[str, Any]:
            return {
                "status": value.status.value,
                "value": value.value,
                "evidence_ref": value.evidence_ref,
            }

        return {
            "schema_version": schema_version,
            "intention_id": intention_id,
            "program": program,
            "repository": repository,
            "branch": branch,
            "head_before": head(head_before),
            "head_after": head(head_after),
        }

    @classmethod
    def expected_receipt_id(
        cls,
        *,
        schema_version: str,
        intention_id: str,
        program: str,
        repository: str,
        branch: str,
        head_before: EvidenceValue[str],
        head_after: EvidenceValue[str],
    ) -> str:
        payload = cls.canonical_payload(
            schema_version=schema_version,
            intention_id=intention_id,
            program=program,
            repository=repository,
            branch=branch,
            head_before=head_before,
            head_after=head_after,
        )
        serialized = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        return sha256(serialized.encode("utf-8")).hexdigest()

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported_schema_version")
        for value in (self.head_before, self.head_after, self.files_changed):
            value.validate()
        for change in self.files_changed.value or ():
            change.validate()
        if self.head_before.status.value == "OBSERVED" and not _SHA_RE.fullmatch(
            self.head_before.value or ""
        ):
            raise ValueError("invalid_head_before")
        if self.head_after.status.value == "OBSERVED" and not _SHA_RE.fullmatch(
            self.head_after.value or ""
        ):
            raise ValueError("invalid_head_after")
        if (
            not self.intention_id.strip()
            or not self.repository.strip()
            or not self.branch.strip()
        ):
            raise ValueError("required_identity_missing")
        self.test_result.validate()
        self.build_result.validate()
        self.runtime_result.validate()
        for reference in self.evidence_references:
            reference.validate()
        self.executor.validate()
        if self.reviewer is not None:
            self.reviewer.validate()
        expected = self.expected_receipt_id(
            schema_version=self.schema_version,
            intention_id=self.intention_id,
            program=self.program,
            repository=self.repository,
            branch=self.branch,
            head_before=self.head_before,
            head_after=self.head_after,
        )
        if self.receipt_id != expected:
            raise ValueError("receipt_id_mismatch")

    def canonical_json(self) -> str:
        self.validate()
        return json.dumps(
            self._full_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def _full_payload(self) -> dict[str, Any]:
        def evidence_value(value: EvidenceValue[Any]) -> dict[str, Any]:
            payload: dict[str, Any] = {
                "status": value.status.value,
                "evidence_ref": value.evidence_ref,
            }
            if isinstance(value.value, tuple):
                payload["value"] = [
                    {
                        "path": item.path,
                        "change_type": item.change_type,
                        "before_blob_sha": item.before_blob_sha,
                        "after_blob_sha": item.after_blob_sha,
                    }
                    if isinstance(item, FileChange)
                    else item
                    for item in value.value
                ]
            else:
                payload["value"] = value.value
            return payload

        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "intention_id": self.intention_id,
            "program": self.program,
            "repository": self.repository,
            "branch": self.branch,
            "head_before": evidence_value(self.head_before),
            "head_after": evidence_value(self.head_after),
            "files_changed": evidence_value(self.files_changed),
            "test_commands": self.test_commands,
            "test_result": self.test_result.__dict__,
            "build_result": self.build_result.__dict__,
            "runtime_result": self.runtime_result.__dict__,
            "evidence_references": [item.__dict__ for item in self.evidence_references],
            "decision": self.decision.__dict__,
            "created_at": self.created_at,
            "executor": self.executor.__dict__,
            "reviewer": self.reviewer.__dict__ if self.reviewer else None,
        }
