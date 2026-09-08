from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


UNKNOWN = "UNKNOWN"


class Outcome(StrEnum):
    PROGRESS = "Progress"
    NO_PROGRESS = "NoProgress"
    FAIL = "Fail"


class StopReason(StrEnum):
    NONE = "NONE"
    NO_PROGRESS = "NO_PROGRESS"
    FAIL = "FAIL"
    BOUND_COMPLETE = "BOUND_COMPLETE"
    VOID_IDENTITY = "VOID_IDENTITY"
    VOID_PROTOCOL = "VOID_PROTOCOL"
    ABORT_SAFETY = "ABORT_SAFETY"


@dataclass(frozen=True)
class L1Checkpoint:
    generation_id: str
    l0_profile_id: str
    authority_envelope_hash: str
    namespace: str
    allowed_tools: tuple[str, ...]
    writer_id: str | None
    stopped: bool
    stop_reason: StopReason
    mutation_count: int


class L1QualificationRuntime:
    """Synthetic, non-production OCS-X L1 qualification surface."""

    def __init__(
        self,
        *,
        generation_id: str = "OCSX-L1-QUALIFICATION-001",
        l0_profile_id: str = "L0_FROZEN_V1",
        namespace: str = "ocsx://experiment/l1-qualification",
        allowed_tools: frozenset[str] | None = None,
        progress_monitor_enabled: bool = True,
    ) -> None:
        self.generation_id = generation_id
        self.l0_profile_id = l0_profile_id
        self.namespace = namespace
        self.allowed_tools = frozenset() if allowed_tools is None else frozenset(allowed_tools)
        self.progress_monitor_enabled = progress_monitor_enabled
        self.writer_id: str | None = None
        self.stopped = False
        self.stop_reason = StopReason.NONE
        self.mutation_count = 0

    @staticmethod
    def _hash(payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        return hashlib.sha256(encoded).hexdigest()

    @property
    def authority_envelope_hash(self) -> str:
        return self._hash(
            {
                "l0_profile_id": self.l0_profile_id,
                "namespace": self.namespace,
                "allowed_tools": sorted(self.allowed_tools),
            }
        )

    def bind_writer(self, writer_id: str) -> bool:
        if self.stopped:
            return False
        if self.writer_id is None:
            self.writer_id = writer_id
            return True
        return self.writer_id == writer_id

    @staticmethod
    def classify_outcome(
        *,
        material_progress: bool,
        structural_failure: bool,
        admissible_evidence_count: int,
    ) -> Outcome | str:
        if structural_failure:
            return Outcome.FAIL
        if material_progress:
            return Outcome.PROGRESS
        if admissible_evidence_count < 0:
            return UNKNOWN
        return Outcome.NO_PROGRESS

    def apply_outcome(self, outcome: Outcome | str) -> StopReason:
        if self.stopped:
            return self.stop_reason
        if outcome == UNKNOWN:
            return StopReason.NONE
        if outcome is Outcome.FAIL:
            self.stop(StopReason.FAIL)
        elif outcome is Outcome.NO_PROGRESS and self.progress_monitor_enabled:
            self.stop(StopReason.NO_PROGRESS)
        return self.stop_reason

    def stop(self, reason: StopReason) -> bool:
        if reason is StopReason.NONE:
            raise ValueError("terminal stop requires reason")
        if self.stopped:
            return False
        self.stopped = True
        self.stop_reason = reason
        return True

    def request_effect(
        self,
        *,
        writer_id: str,
        target_namespace: str,
        surface: str,
        tool: str | None = None,
    ) -> bool:
        forbidden_surface = surface in {"canonical", "ouro", "production"}
        tool_ok = tool is None if not self.allowed_tools else tool in self.allowed_tools
        allowed = (
            not self.stopped
            and self.writer_id == writer_id
            and target_namespace == self.namespace
            and not forbidden_surface
            and tool_ok
        )
        if not allowed:
            return False
        self.mutation_count += 1
        return True

    def checkpoint(self) -> L1Checkpoint:
        return L1Checkpoint(
            generation_id=self.generation_id,
            l0_profile_id=self.l0_profile_id,
            authority_envelope_hash=self.authority_envelope_hash,
            namespace=self.namespace,
            allowed_tools=tuple(sorted(self.allowed_tools)),
            writer_id=self.writer_id,
            stopped=self.stopped,
            stop_reason=self.stop_reason,
            mutation_count=self.mutation_count,
        )

    @classmethod
    def recover(
        cls,
        checkpoint: L1Checkpoint,
        *,
        expected_l0_profile_id: str,
        expected_authority_envelope_hash: str,
        expected_namespace: str,
    ) -> "L1QualificationRuntime":
        if checkpoint.l0_profile_id != expected_l0_profile_id:
            raise ValueError(StopReason.VOID_IDENTITY)
        if checkpoint.namespace != expected_namespace:
            raise ValueError(StopReason.VOID_PROTOCOL)
        recovered = cls(
            generation_id=checkpoint.generation_id,
            l0_profile_id=checkpoint.l0_profile_id,
            namespace=checkpoint.namespace,
            allowed_tools=frozenset(checkpoint.allowed_tools),
        )
        recovered.writer_id = checkpoint.writer_id
        recovered.stopped = checkpoint.stopped
        recovered.stop_reason = checkpoint.stop_reason
        recovered.mutation_count = checkpoint.mutation_count
        if recovered.authority_envelope_hash != expected_authority_envelope_hash:
            raise ValueError(StopReason.VOID_PROTOCOL)
        return recovered

    @staticmethod
    def checkpoint_hash(checkpoint: L1Checkpoint) -> str:
        return L1QualificationRuntime._hash(asdict(checkpoint))

    @staticmethod
    def evidence_value(values: dict[str, Any], key: str) -> Any:
        return values.get(key, UNKNOWN)
