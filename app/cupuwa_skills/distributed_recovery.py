from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RecoveryDecision(StrEnum):
    RECONCILE = "RECONCILE"
    RETRY = "RETRY"
    HOLD = "HOLD"


@dataclass(frozen=True)
class RecoveryObservation:
    operation_id: str
    state: str
    effect_observed: bool | None
    idempotency_verified: bool
    receipt_readable: bool


def decide_recovery(observation: RecoveryObservation) -> RecoveryDecision:
    if observation.receipt_readable and observation.effect_observed is True:
        return RecoveryDecision.RECONCILE

    if observation.effect_observed is False and observation.idempotency_verified:
        return RecoveryDecision.RETRY

    return RecoveryDecision.HOLD
