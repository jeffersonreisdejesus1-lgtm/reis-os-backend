from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Decision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class GenerationStatus(StrEnum):
    PREPARED = "PREPARED"
    STOPPED = "STOPPED"
    VOID = "VOID"
    ABORTED = "ABORTED"


class StopReason(StrEnum):
    NONE = "NONE"
    BOUND_COMPLETE = "BOUND_COMPLETE"
    NO_PROGRESS = "NO_PROGRESS"
    FAIL = "FAIL"
    VOID_IDENTITY = "VOID_IDENTITY"
    VOID_PROTOCOL = "VOID_PROTOCOL"
    ABORT_SAFETY = "ABORT_SAFETY"


@dataclass(frozen=True)
class EvidenceEvent:
    sequence: int
    kind: str
    payload_hash: str
    previous_hash: str
    event_hash: str


@dataclass(frozen=True)
class PretrialCheckpoint:
    generation_id: str
    l0_hash: str
    authority_envelope_hash: str
    namespace: str
    writer_id: str | None
    stopped: bool
    stop_reason: StopReason
    mutation_count: int
    evidence_cursor: int


@dataclass(frozen=True)
class GenerationRecord:
    generation_id: str
    status: GenerationStatus
    stop_reason: StopReason
    evidence_head: str
    mutation_count: int


@dataclass
class SyntheticPretrialHarness:
    """In-memory enforcement proof surface; never performs external effects."""

    generation_id: str = "OCSX-PRETRIAL-SYNTHETIC-001"
    namespace: str = "ocsx://experiment/pretrial"
    l0_hash: str = "L0_FROZEN_V1"
    allowed_tools: frozenset[str] = frozenset({"synthetic-read", "synthetic-write"})
    external_gate_token: str = "EXTERNAL_SYNTHETIC_GATE"
    writer_id: str | None = None
    stopped: bool = False
    stop_reason: StopReason = StopReason.NONE
    mutation_count: int = 0
    proposals: dict[str, dict[str, str]] = field(default_factory=dict)
    events: list[EvidenceEvent] = field(default_factory=list)
    records: list[GenerationRecord] = field(default_factory=list)

    @property
    def authority_envelope_hash(self) -> str:
        payload = {
            "allowed_tools": sorted(self.allowed_tools),
            "l0_hash": self.l0_hash,
            "namespace": self.namespace,
        }
        return self._hash_json(payload)

    @staticmethod
    def _hash_json(payload: Any) -> str:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode()
        return hashlib.sha256(encoded).hexdigest()

    def _journal(self, kind: str, payload: dict[str, Any]) -> EvidenceEvent:
        previous_hash = self.events[-1].event_hash if self.events else "GENESIS"
        payload_hash = self._hash_json(payload)
        event_hash = self._hash_json(
            {
                "sequence": len(self.events) + 1,
                "kind": kind,
                "payload_hash": payload_hash,
                "previous_hash": previous_hash,
            }
        )
        event = EvidenceEvent(
            sequence=len(self.events) + 1,
            kind=kind,
            payload_hash=payload_hash,
            previous_hash=previous_hash,
            event_hash=event_hash,
        )
        self.events.append(event)
        return event

    def bind_writer(self, writer_id: str) -> Decision:
        if self.stopped:
            self._journal("WRITER_DENY_STOPPED", {"writer_id": writer_id})
            return Decision.DENY
        if self.writer_id is None:
            self.writer_id = writer_id
            self._journal("WRITER_BOUND", {"writer_id": writer_id})
            return Decision.ALLOW
        if self.writer_id == writer_id:
            return Decision.ALLOW
        self._journal(
            "WRITER_DENY_SECONDARY",
            {"active_writer": self.writer_id, "requested_writer": writer_id},
        )
        return Decision.DENY

    def sanitize_cognitive_input(self, payload: dict[str, Any]) -> dict[str, Any]:
        forbidden = {"router_state", "internal_route", "ouro", "authority_token"}
        sanitized = {key: value for key, value in payload.items() if key not in forbidden}
        removed = sorted(set(payload) - set(sanitized))
        self._journal("COGNITIVE_INPUT_SANITIZED", {"removed": removed})
        return sanitized

    def request_mutation(
        self,
        *,
        target_namespace: str,
        surface: str,
        writer_id: str,
        tool: str = "synthetic-write",
    ) -> Decision:
        before = self.mutation_count
        denied_surface = surface in {"canonical", "ouro", "production"}
        allowed = (
            not self.stopped
            and self.writer_id == writer_id
            and target_namespace == self.namespace
            and not denied_surface
            and tool in self.allowed_tools
        )
        if not allowed:
            self._journal(
                "MUTATION_DENIED",
                {
                    "surface": surface,
                    "target_namespace": target_namespace,
                    "tool": tool,
                    "mutation_count_before": before,
                    "mutation_count_after": self.mutation_count,
                },
            )
            return Decision.DENY
        self.mutation_count += 1
        self._journal(
            "SYNTHETIC_MUTATION",
            {
                "surface": surface,
                "target_namespace": target_namespace,
                "tool": tool,
                "mutation_count": self.mutation_count,
            },
        )
        return Decision.ALLOW

    def propose(self, proposal_id: str, *, target_namespace: str, surface: str) -> None:
        self.proposals[proposal_id] = {
            "target_namespace": target_namespace,
            "surface": surface,
        }
        self._journal("PROPOSAL_RECORDED", {"proposal_id": proposal_id})

    def simulate_gated_effect(
        self,
        proposal_id: str,
        *,
        gate_token: str | None,
        writer_id: str,
    ) -> Decision:
        proposal = self.proposals.get(proposal_id)
        if proposal is None or gate_token != self.external_gate_token:
            self._journal("PROPOSAL_EXECUTION_DENIED", {"proposal_id": proposal_id})
            return Decision.DENY
        return self.request_mutation(
            target_namespace=proposal["target_namespace"],
            surface=proposal["surface"],
            writer_id=writer_id,
        )

    def stop(self, reason: StopReason) -> Decision:
        if self.stopped:
            self._journal(
                "SECOND_STOP_DENIED",
                {"existing_reason": self.stop_reason, "requested_reason": reason},
            )
            return Decision.DENY
        if reason is StopReason.NONE:
            raise ValueError("terminal stop requires a non-NONE reason")
        self.stopped = True
        self.stop_reason = reason
        self._journal("STOP_COMMITTED", {"reason": reason})
        return Decision.ALLOW

    def checkpoint(self) -> PretrialCheckpoint:
        return PretrialCheckpoint(
            generation_id=self.generation_id,
            l0_hash=self.l0_hash,
            authority_envelope_hash=self.authority_envelope_hash,
            namespace=self.namespace,
            writer_id=self.writer_id,
            stopped=self.stopped,
            stop_reason=self.stop_reason,
            mutation_count=self.mutation_count,
            evidence_cursor=len(self.events),
        )

    @classmethod
    def recover(
        cls,
        checkpoint: PretrialCheckpoint,
        *,
        expected_l0_hash: str,
        expected_authority_envelope_hash: str,
        expected_namespace: str,
        allowed_tools: frozenset[str] | None = None,
    ) -> SyntheticPretrialHarness:
        if checkpoint.l0_hash != expected_l0_hash:
            raise ValueError(StopReason.VOID_IDENTITY)
        if checkpoint.authority_envelope_hash != expected_authority_envelope_hash:
            raise ValueError(StopReason.VOID_PROTOCOL)
        if checkpoint.namespace != expected_namespace:
            raise ValueError(StopReason.VOID_PROTOCOL)
        recovered = cls(
            generation_id=checkpoint.generation_id,
            namespace=checkpoint.namespace,
            l0_hash=checkpoint.l0_hash,
            allowed_tools=allowed_tools or frozenset({"synthetic-read", "synthetic-write"}),
            writer_id=checkpoint.writer_id,
            stopped=checkpoint.stopped,
            stop_reason=checkpoint.stop_reason,
            mutation_count=checkpoint.mutation_count,
        )
        if recovered.authority_envelope_hash != expected_authority_envelope_hash:
            raise ValueError(StopReason.VOID_PROTOCOL)
        recovered._journal(
            "RECOVERED",
            {
                "evidence_cursor": checkpoint.evidence_cursor,
                "stopped": checkpoint.stopped,
                "stop_reason": checkpoint.stop_reason,
            },
        )
        return recovered

    def seal_record(self, status: GenerationStatus) -> GenerationRecord:
        if status is GenerationStatus.PREPARED:
            raise ValueError("terminal record cannot be PREPARED")
        head = self.events[-1].event_hash if self.events else "GENESIS"
        record = GenerationRecord(
            generation_id=self.generation_id,
            status=status,
            stop_reason=self.stop_reason,
            evidence_head=head,
            mutation_count=self.mutation_count,
        )
        self.records.append(record)
        return record

    def metric_value(self, values: dict[str, int | float | str], metric_id: str) -> Any:
        return values.get(metric_id, "UNKNOWN")

    def verify_evidence_chain(self) -> bool:
        previous = "GENESIS"
        for event in self.events:
            expected = self._hash_json(
                {
                    "sequence": event.sequence,
                    "kind": event.kind,
                    "payload_hash": event.payload_hash,
                    "previous_hash": previous,
                }
            )
            if event.previous_hash != previous or event.event_hash != expected:
                return False
            previous = event.event_hash
        return True

    @staticmethod
    def checkpoint_hash(checkpoint: PretrialCheckpoint) -> str:
        return SyntheticPretrialHarness._hash_json(asdict(checkpoint))
