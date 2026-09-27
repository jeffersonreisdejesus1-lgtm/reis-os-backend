from dataclasses import dataclass

import pytest

from app.visual_orchestrator import NormativeUnit, VisualOrchestrator
from app.visual_orchestrator.core import ProviderReceipt


def rule(
    unit_id: str,
    scope: str,
    specificity: int,
    invariant: str,
    materialization: str,
    *,
    status: str = "VIGENTE",
    superseded_by: str | None = None,
) -> NormativeUnit:
    return NormativeUnit(
        unit_id=unit_id,
        source="notion",
        scope=scope,
        authority="Jefferson Reis",
        temporal_status=status,
        specificity=specificity,
        invariant=invariant,
        materialization=materialization,
        superseded_by=superseded_by,
    )


@dataclass
class FakeProvider:
    name: str = "test-provider"
    stored: bytes = b"artifact"

    def execute(self, contract):
        return ProviderReceipt(
            provider=self.name,
            effect_id="effect-1",
            artifact_ref="artifact://1",
            contract_digest=contract.digest(),
        )

    def readback(self, artifact_ref: str) -> bytes:
        assert artifact_ref == "artifact://1"
        return self.stored


def test_specific_rule_specializes_global_without_reopening_history():
    engine = VisualOrchestrator(
        [
            rule("global", "GLOBAL", 1, "layer2", "old"),
            rule("current", "Artificial Real", 2, "layer2", "v1.1"),
            rule(
                "historic",
                "Artificial Real",
                3,
                "layer2",
                "post-overlay",
                status="SUPERSEDED",
                superseded_by="current",
            ),
        ]
    )
    resolved = engine.resolve_rules(("GLOBAL", "Artificial Real"))
    assert [r.unit_id for r in resolved] == ["current"]


def test_contract_is_deterministic_and_copy_is_literal():
    engine = VisualOrchestrator([rule("copy-lock", "GLOBAL", 1, "copy", "literal")])
    kwargs = dict(
        mission_id="M1",
        brand="Jefferson Reis",
        language="Artificial Real",
        artifact_id="carousel-03",
        card_id="01",
        canonical_copy="Texto canônico.",
        provider="test-provider",
    )
    first = engine.contract(**kwargs)
    second = engine.contract(**kwargs)
    assert first.idempotency_key == second.idempotency_key
    assert first.digest() == second.digest()
    assert first.canonical_copy == "Texto canônico."


def test_empty_copy_fails_closed():
    with pytest.raises(ValueError):
        VisualOrchestrator().contract(
            mission_id="M1",
            brand="Jefferson Reis",
            language="Artificial Real",
            artifact_id="carousel-03",
            card_id="01",
            canonical_copy=" ",
            provider="test-provider",
        )


def test_provider_boundary_fails_closed():
    contract = VisualOrchestrator().contract(
        mission_id="M1",
        brand="Jefferson Reis",
        language="Artificial Real",
        artifact_id="carousel-03",
        card_id="01",
        canonical_copy="x",
        provider="expected",
    )
    with pytest.raises(PermissionError):
        VisualOrchestrator().execute(contract, FakeProvider())


def test_execute_and_independent_readback_reconcile():
    provider = FakeProvider()
    engine = VisualOrchestrator()
    contract = engine.contract(
        mission_id="M1",
        brand="Jefferson Reis",
        language="Artificial Real",
        artifact_id="carousel-03",
        card_id="01",
        canonical_copy="x",
        provider=provider.name,
    )
    receipt = engine.execute(contract, provider)
    assert engine.reconcile(contract, receipt, provider) == b"artifact"
