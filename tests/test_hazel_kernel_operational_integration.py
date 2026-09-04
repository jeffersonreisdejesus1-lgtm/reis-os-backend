from __future__ import annotations

# ruff: noqa: E501, I001

from hashlib import sha256
import json
from pathlib import Path

import pytest

from app.universal_kernel.hazel_continuity import HazelBoundContinuity, HazelIntegrationError
from app.universal_kernel.identity import IdentityAuditLog, IdentityKernelGuard


class FakeHazelTransport:
    def __init__(self) -> None:
        self.latest: dict[tuple[str, str, str], dict] = {}
        self.persist_calls = 0
        self.recover_calls = 0

    @staticmethod
    def _payload_hash(payload: dict) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return sha256(raw.encode()).hexdigest()

    @staticmethod
    def _event_hash(envelope: dict) -> str:
        raw = {**envelope, "payload_hash": FakeHazelTransport._payload_hash(envelope["payload"])}
        encoded = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return sha256(encoded.encode()).hexdigest()

    def persist(self, envelope: dict) -> dict:
        self.persist_calls += 1
        key = (envelope["run_id"], envelope["ocs_id"], envelope["state_namespace"])
        previous = self.latest.get(key)
        if previous is None:
            assert envelope["predecessor_hash"] is None
            assert envelope["state_version"] == 1
        else:
            if envelope["predecessor_hash"] != previous["event_hash"]:
                raise RuntimeError("predecessor_mismatch")
        payload_hash = self._payload_hash(envelope["payload"])
        event_hash = self._event_hash(envelope)
        receipt = {
            "accepted": True,
            "reason": "persisted",
            "run_id": envelope["run_id"],
            "ocs_id": envelope["ocs_id"],
            "state_namespace": envelope["state_namespace"],
            "memory_namespace": envelope["memory_namespace"],
            "authority_ref": envelope["authority_ref"],
            "binding_hash": envelope["binding_hash"],
            "state_version": envelope["state_version"],
            "payload": envelope["payload"],
            "payload_hash": payload_hash,
            "event_hash": event_hash,
            "predecessor_hash": envelope["predecessor_hash"],
            "trace_id": envelope["trace_id"],
        }
        self.latest[key] = receipt
        return receipt

    def recover(self, request: dict) -> dict:
        self.recover_calls += 1
        key = (request["run_id"], request["ocs_id"], request["state_namespace"])
        value = dict(self.latest[key])
        for field in ("memory_namespace", "authority_ref", "binding_hash"):
            if value[field] != request[field]:
                raise RuntimeError(f"{field}_mismatch")
        return value


def build(tmp_path: Path) -> tuple[IdentityKernelGuard, FakeHazelTransport, HazelBoundContinuity]:
    audit = IdentityAuditLog(tmp_path / "identity.jsonl")
    guard = IdentityKernelGuard(audit_log=audit)
    transport = FakeHazelTransport()
    continuity = HazelBoundContinuity(guard=guard, transport=transport)
    return guard, transport, continuity


def test_kernel_to_hazel_requires_pre_persist_identity_gate_and_authority(tmp_path: Path) -> None:
    guard, transport, continuity = build(tmp_path)
    binding = guard.bind_active_identity(run_id="r1", ocs_id="NÓESIS", host="ChatGPT", session_context="s1")
    result = continuity.persist_state(
        run_id="r1",
        expected_ocs="NÓESIS",
        host="ChatGPT",
        authority_ref=binding.authority_envelope_ref,
        state_version=1,
        predecessor_hash=None,
        state={"program_state": "active"},
        trace_id="t1",
    )
    assert result.receipt["accepted"] is True
    assert transport.persist_calls == 1
    assert any(e.event_type == "IDENTITY_REVALIDATION" and e.details.get("trigger") == "pre_persist" for e in guard.audit_log.events)
    assert any(e.event_type == "HAZEL_PERSIST_RECEIPT" for e in guard.audit_log.events)

    with pytest.raises(HazelIntegrationError, match="authority_ref_mismatch"):
        continuity.persist_state(
            run_id="r1", expected_ocs="NÓESIS", host="ChatGPT", authority_ref="authority://forged",
            state_version=2, predecessor_hash=result.receipt["event_hash"], state={"x": 2}, trace_id="t2"
        )
    assert transport.persist_calls == 1


def test_cross_ocs_or_host_drift_fails_before_hazel_mutation(tmp_path: Path) -> None:
    guard, transport, continuity = build(tmp_path)
    binding = guard.bind_active_identity(run_id="r1", ocs_id="NÓESIS", host="ChatGPT", session_context="s1")
    with pytest.raises(ValueError, match="active_ocs_identity_mismatch"):
        continuity.persist_state(
            run_id="r1", expected_ocs="SOFIA", host="ChatGPT", authority_ref=binding.authority_envelope_ref,
            state_version=1, predecessor_hash=None, state={"x": 1}, trace_id="t1"
        )
    assert transport.persist_calls == 0


def test_cold_start_recovery_uses_local_identity_then_hazel_and_readback(tmp_path: Path) -> None:
    audit_path = tmp_path / "identity.jsonl"
    guard = IdentityKernelGuard(audit_log=IdentityAuditLog(audit_path))
    transport = FakeHazelTransport()
    continuity = HazelBoundContinuity(guard=guard, transport=transport)
    binding = guard.bind_active_identity(run_id="r1", ocs_id="NÓESIS", host="ChatGPT", session_context="s1")
    persisted = continuity.persist_state(
        run_id="r1", expected_ocs="NÓESIS", host="ChatGPT", authority_ref=binding.authority_envelope_ref,
        state_version=1, predecessor_hash=None, state={"state": "durable"}, trace_id="t1"
    )

    restarted_guard = IdentityKernelGuard(audit_log=IdentityAuditLog(audit_path))
    restarted = HazelBoundContinuity(guard=restarted_guard, transport=transport)
    recovered = restarted.recover_state(
        run_id="r1", expected_ocs="NÓESIS", host="ChatGPT", authority_ref=binding.authority_envelope_ref
    )
    assert recovered["payload"] == {"state": "durable"}
    assert recovered["payload_hash"] == persisted.receipt["payload_hash"]
    assert transport.recover_calls == 1
    assert any(e.event_type == "RECOVER_IDENTITY" for e in restarted_guard.audit_log.events)
    assert any(e.event_type == "HAZEL_RECOVERY_ACCEPTED" for e in restarted_guard.audit_log.events)


def test_recovery_payload_corruption_fails_closed(tmp_path: Path) -> None:
    guard, transport, continuity = build(tmp_path)
    binding = guard.bind_active_identity(run_id="r1", ocs_id="NÓESIS", host="ChatGPT", session_context="s1")
    continuity.persist_state(
        run_id="r1", expected_ocs="NÓESIS", host="ChatGPT", authority_ref=binding.authority_envelope_ref,
        state_version=1, predecessor_hash=None, state={"state": "durable"}, trace_id="t1"
    )
    key = ("r1", "NÓESIS", binding.state_namespace)
    transport.latest[key]["payload"] = {"tampered": True}
    with pytest.raises(HazelIntegrationError, match="recovery_payload_integrity_failure"):
        continuity.recover_state(
            run_id="r1", expected_ocs="NÓESIS", host="ChatGPT", authority_ref=binding.authority_envelope_ref
        )
