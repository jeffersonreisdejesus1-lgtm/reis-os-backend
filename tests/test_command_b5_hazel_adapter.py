from __future__ import annotations

# ruff: noqa: E501, I001

from hashlib import sha256
import json
from pathlib import Path

import pytest

from app.command.hazel_adapter import AuthorizedPersistRequest, CommandHazelAdapter
from app.command.kernel_adapter import KernelDecisionReadback
from app.universal_kernel.contracts import AuthorizationDecision
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

    def persist(self, envelope: dict) -> dict:
        self.persist_calls += 1
        payload_hash = self._payload_hash(envelope["payload"])
        canonical = json.dumps(
            {**envelope, "payload_hash": payload_hash},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        event_hash = sha256(canonical.encode()).hexdigest()
        receipt = {
            "accepted": True,
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
        key = (envelope["run_id"], envelope["ocs_id"], envelope["state_namespace"])
        self.latest[key] = receipt
        return receipt

    def recover(self, request: dict) -> dict:
        self.recover_calls += 1
        key = (request["run_id"], request["ocs_id"], request["state_namespace"])
        return dict(self.latest[key])


def _build(tmp_path: Path) -> tuple[IdentityKernelGuard, FakeHazelTransport, CommandHazelAdapter]:
    guard = IdentityKernelGuard(audit_log=IdentityAuditLog(tmp_path / "identity.jsonl"))
    transport = FakeHazelTransport()
    hazel = HazelBoundContinuity(guard=guard, transport=transport)
    return guard, transport, CommandHazelAdapter(hazel)


def _decision(authority_ref: str, decision: AuthorizationDecision = AuthorizationDecision.ALLOW) -> KernelDecisionReadback:
    return KernelDecisionReadback(
        intent_id="intent-b5-001",
        decision=decision,
        reason="authorized" if decision is AuthorizationDecision.ALLOW else "denied",
        organization="REIS-OS",
        scope=("command:state:persist",),
        expected_state_ref="state:command:1",
        expected_state_version=0,
        idempotency_key="idem-b5-001",
        correlation_id="corr-b5-001",
        causation_id="cause-b5-000",
        trace_id="trace-b5-001",
        authority_ref=authority_ref,
        policy_snapshot="policy:b5:v1",
        envelope_issued=decision is AuthorizationDecision.ALLOW,
    )


def _request(*, version: int = 1, predecessor: str | None = None) -> AuthorizedPersistRequest:
    return AuthorizedPersistRequest(
        run_id="run-b5-001",
        ocs="ÁGORA",
        host="ChatGPT",
        state_version=version,
        predecessor_hash=predecessor,
        state={"program_state": "active", "version": version},
        idempotency_key="idem-b5-001",
        correlation_id="corr-b5-001",
        causation_id="cause-b5-000",
    )


def test_b5_allow_persists_then_reads_back_recoverable_state(tmp_path: Path) -> None:
    guard, transport, adapter = _build(tmp_path)
    binding = guard.bind_active_identity(
        run_id="run-b5-001", ocs_id="ÁGORA", host="ChatGPT", session_context="b5"
    )

    result = adapter.persist(_decision(binding.authority_envelope_ref), _request())

    assert result.persisted is True
    assert result.recovered is True
    assert result.mutation_count == 1
    assert result.state_version == 1
    assert result.event_hash
    assert result.payload_hash
    assert transport.persist_calls == 1
    assert transport.recover_calls == 1


def test_b5_deny_never_crosses_hazel_mutation_boundary(tmp_path: Path) -> None:
    guard, transport, adapter = _build(tmp_path)
    binding = guard.bind_active_identity(
        run_id="run-b5-001", ocs_id="ÁGORA", host="ChatGPT", session_context="b5"
    )

    result = adapter.persist(
        _decision(binding.authority_envelope_ref, AuthorizationDecision.DENY),
        _request(),
    )

    assert result.persisted is False
    assert result.mutation_count == 0
    assert transport.persist_calls == 0
    assert transport.recover_calls == 0


def test_b5_idempotent_replay_causes_zero_additional_mutations(tmp_path: Path) -> None:
    guard, transport, adapter = _build(tmp_path)
    binding = guard.bind_active_identity(
        run_id="run-b5-001", ocs_id="ÁGORA", host="ChatGPT", session_context="b5"
    )
    decision = _decision(binding.authority_envelope_ref)

    first = adapter.persist(decision, _request())
    second = adapter.persist(decision, _request())

    assert first.mutation_count == 1
    assert second.idempotent_replay is True
    assert second.mutation_count == 1
    assert transport.persist_calls == 1


def test_b5_predecessor_drift_fails_before_second_persist(tmp_path: Path) -> None:
    guard, transport, adapter = _build(tmp_path)
    binding = guard.bind_active_identity(
        run_id="run-b5-001", ocs_id="ÁGORA", host="ChatGPT", session_context="b5"
    )
    decision = _decision(binding.authority_envelope_ref)
    first = adapter.persist(decision, _request())
    assert first.event_hash is not None

    with pytest.raises(HazelIntegrationError, match="command_hazel_predecessor_drift"):
        adapter.persist(
            KernelDecisionReadback(
                **{
                    **decision.__dict__,
                    "idempotency_key": "idem-b5-002",
                    "correlation_id": "corr-b5-002",
                    "causation_id": "cause-b5-001",
                }
            ),
            AuthorizedPersistRequest(
                **{
                    **_request(version=2, predecessor="wrong-predecessor").__dict__,
                    "idempotency_key": "idem-b5-002",
                    "correlation_id": "corr-b5-002",
                    "causation_id": "cause-b5-001",
                }
            ),
        )
    assert transport.persist_calls == 1


def test_b5_invalid_causal_binding_fails_before_hazel(tmp_path: Path) -> None:
    guard, transport, adapter = _build(tmp_path)
    binding = guard.bind_active_identity(
        run_id="run-b5-001", ocs_id="ÁGORA", host="ChatGPT", session_context="b5"
    )
    request = AuthorizedPersistRequest(
        **{**_request().__dict__, "correlation_id": "corr-forged"}
    )

    with pytest.raises(HazelIntegrationError, match="command_hazel_correlation_binding_mismatch"):
        adapter.persist(_decision(binding.authority_envelope_ref), request)
    assert transport.persist_calls == 0


def test_b5_namespace_drift_and_corruption_fail_closed(tmp_path: Path) -> None:
    guard, transport, adapter = _build(tmp_path)
    binding = guard.bind_active_identity(
        run_id="run-b5-001", ocs_id="ÁGORA", host="ChatGPT", session_context="b5"
    )
    decision = _decision(binding.authority_envelope_ref)
    adapter.persist(decision, _request())
    key = ("run-b5-001", "ÁGORA", binding.state_namespace)

    transport.latest[key]["state_namespace"] = "foreign-namespace"
    with pytest.raises(HazelIntegrationError, match="recovery_namespace_mismatch"):
        adapter.recover(decision, run_id="run-b5-001", ocs="ÁGORA", host="ChatGPT")

    transport.latest[key]["state_namespace"] = binding.state_namespace
    transport.latest[key]["payload"] = {"tampered": True}
    with pytest.raises(HazelIntegrationError, match="recovery_payload_integrity_failure"):
        adapter.recover(decision, run_id="run-b5-001", ocs="ÁGORA", host="ChatGPT")
