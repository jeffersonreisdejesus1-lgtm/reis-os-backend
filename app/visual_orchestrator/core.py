from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Protocol


class ArtifactState(StrEnum):
    DRAFT = "DRAFT"
    CONTRACTED = "CONTRACTED"
    EXECUTED = "EXECUTED"
    VALIDATED = "VALIDATED"
    RECONCILED = "RECONCILED"
    APPROVED = "APPROVED"
    HOLD = "HOLD"


@dataclass(frozen=True)
class NormativeUnit:
    unit_id: str
    source: str
    scope: str
    authority: str
    temporal_status: str
    specificity: int
    invariant: str
    materialization: str
    supersedes: tuple[str, ...] = ()
    superseded_by: str | None = None

    @property
    def executable(self) -> bool:
        return self.temporal_status == "VIGENTE" and self.superseded_by is None


@dataclass(frozen=True)
class ExecutionContract:
    mission_id: str
    brand: str
    language: str
    artifact_id: str
    card_id: str
    canonical_copy: str
    rules: tuple[NormativeUnit, ...]
    provider: str
    idempotency_key: str

    def digest(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class ProviderReceipt:
    provider: str
    effect_id: str
    artifact_ref: str
    contract_digest: str


class MaterialProvider(Protocol):
    name: str

    def execute(self, contract: ExecutionContract) -> ProviderReceipt: ...

    def readback(self, artifact_ref: str) -> bytes: ...


@dataclass
class VisualOrchestrator:
    rules: list[NormativeUnit] = field(default_factory=list)

    def resolve_rules(self, scopes: tuple[str, ...]) -> tuple[NormativeUnit, ...]:
        candidates = [r for r in self.rules if r.executable and r.scope in scopes]
        winners: dict[str, NormativeUnit] = {}
        for rule in sorted(candidates, key=lambda r: r.specificity):
            current = winners.get(rule.invariant)
            if current is None or rule.specificity >= current.specificity:
                winners[rule.invariant] = rule
        return tuple(sorted(winners.values(), key=lambda r: r.unit_id))

    def contract(
        self,
        *,
        mission_id: str,
        brand: str,
        language: str,
        artifact_id: str,
        card_id: str,
        canonical_copy: str,
        provider: str,
    ) -> ExecutionContract:
        if not canonical_copy.strip():
            raise ValueError("canonical copy is required")
        rules = self.resolve_rules(("GLOBAL", language, artifact_id, card_id))
        seed = "|".join((mission_id, artifact_id, card_id, canonical_copy, provider))
        key = hashlib.sha256(seed.encode()).hexdigest()
        return ExecutionContract(
            mission_id=mission_id,
            brand=brand,
            language=language,
            artifact_id=artifact_id,
            card_id=card_id,
            canonical_copy=canonical_copy,
            rules=rules,
            provider=provider,
            idempotency_key=key,
        )

    def execute(
        self, contract: ExecutionContract, provider: MaterialProvider
    ) -> ProviderReceipt:
        if provider.name != contract.provider:
            raise PermissionError("provider boundary mismatch")
        receipt = provider.execute(contract)
        if receipt.contract_digest != contract.digest():
            raise RuntimeError("provider receipt contract drift")
        return receipt

    def reconcile(
        self,
        contract: ExecutionContract,
        receipt: ProviderReceipt,
        provider: MaterialProvider,
    ) -> bytes:
        if receipt.contract_digest != contract.digest():
            raise RuntimeError("receipt does not reconcile with contract")
        data = provider.readback(receipt.artifact_ref)
        if not data:
            raise RuntimeError("independent readback returned no artifact")
        return data
