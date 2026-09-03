from __future__ import annotations

from dataclasses import replace
from time import time

import pytest

from app.universal_kernel.contracts import MaterialReadback
from app.universal_kernel.effect_recovery import ToolBroker
from app.universal_kernel.governance import (
    AuthenticatedLeaseSnapshot,
    AuthorityLease,
    AuthorityLeaseManager,
    LeaseSnapshot,
)


class Adapter:
    def __init__(self) -> None:
        self.mutations = 0

    def mutate(
        self,
        operation: str,
        payload: dict[str, object],
        idempotency_key: str,
    ) -> str:
        self.mutations += 1
        return f"m-{self.mutations}"

    def readback(self, mutation_id: str) -> MaterialReadback:
        return MaterialReadback(mutation_id, {"value": "mutated"})

    def compensate(
        self,
        operation: str,
        payload: dict[str, object],
        mutation_id: str,
        idempotency_key: str,
    ) -> str:
        return f"c-{mutation_id}"

    def verify_compensation(
        self,
        mutation_id: str,
        readback: MaterialReadback,
    ) -> bool:
        return True


class IndependentVerifier:
    def readback(self, compensation_id: str) -> MaterialReadback:
        original_mutation_id = compensation_id.removeprefix("c-")
        return MaterialReadback(
            compensation_id,
            {"compensated": original_mutation_id},
        )

    def verify(
        self,
        original_mutation_id: str,
        compensation_readback: MaterialReadback,
    ) -> bool:
        return (
            compensation_readback.state.get("compensated")
            == original_mutation_id
        )


def _lease(*, lease_id: str = "lease-1", uses: int = 0) -> AuthorityLease:
    issued = time() - 1
    return AuthorityLease(
        lease_id=lease_id,
        ocs="SOFIA",
        capability="repo.write",
        expires_at=time() + 60,
        actor="SOFIA",
        issued_at=issued,
        not_before=issued,
        scope=("repo.write",),
        tenant="fourth",
        context_ref="context:fourth",
        authority_ref="authority:fourth",
        policy_snapshot="policy:fourth",
        action_binding="repository.write",
        object_ref_or_selector="object:fourth",
        trace_ref="trace:fourth",
        max_uses=3,
        uses_consumed=uses,
    )


def test_f003_python_bypass_forces_claim_narrowing() -> None:
    broker = ToolBroker()
    adapter = Adapter()
    broker.register("repo.write", adapter)
    type(adapter).mutate(adapter, "write", {}, "bypass")
    assert adapter.mutations == 1
    claim = broker.material_boundary_claim()
    assert claim.strength == "IN_PROCESS_GUARD_ONLY"
    assert claim.structural_denial is False


def test_f004_self_attestation_cannot_verify_compensation() -> None:
    broker = ToolBroker()
    adapter = Adapter()
    broker.register("repo.write", adapter)
    assert broker.has_independent_compensation_verifier("repo.write") is False


def test_f004_independent_verifier_is_separate_object() -> None:
    broker = ToolBroker()
    adapter = Adapter()
    verifier = IndependentVerifier()
    broker.register("repo.write", adapter, compensation_verifier=verifier)
    assert broker.has_independent_compensation_verifier("repo.write") is True
    assert verifier is not adapter


def test_f005_unauthenticated_snapshot_restore_is_rejected() -> None:
    raw = (LeaseSnapshot(_lease(), ()),)
    with pytest.raises(ValueError, match="lease_snapshot_authentication_required"):
        AuthorityLeaseManager.from_snapshot(raw)


def test_f005_authenticated_snapshot_requires_exact_index_set() -> None:
    key = b"fourth-round-test-key"
    malformed = LeaseSnapshot(
        _lease(uses=2),
        (("k1", "a1", 1),),
    )
    bundle = AuthenticatedLeaseSnapshot.sign((malformed,), key)
    with pytest.raises(ValueError, match="lease_snapshot_index_set_invalid"):
        AuthorityLeaseManager.from_snapshot(bundle, authentication_key=key)


def test_f005_authenticated_snapshot_rejects_duplicate_indices() -> None:
    key = b"fourth-round-test-key"
    malformed = LeaseSnapshot(
        _lease(uses=2),
        (("k1", "a1", 1), ("k2", "a2", 1)),
    )
    bundle = AuthenticatedLeaseSnapshot.sign((malformed,), key)
    with pytest.raises(ValueError, match="lease_snapshot_index_set_invalid"):
        AuthorityLeaseManager.from_snapshot(bundle, authentication_key=key)


def test_f005_tampered_authenticated_snapshot_is_rejected() -> None:
    key = b"fourth-round-test-key"
    original = AuthenticatedLeaseSnapshot.sign(
        (LeaseSnapshot(_lease(), ()),),
        key,
    )
    tampered = replace(original, mac="00" * 32)
    with pytest.raises(ValueError, match="lease_snapshot_authentication_failed"):
        AuthorityLeaseManager.from_snapshot(tampered, authentication_key=key)
