from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Callable

from .adversarial_failure_bypass import AdversarialProbe


@dataclass(frozen=True, slots=True)
class RuntimeAdversarialEvent:
    attack_class: str
    attempted_action: str
    disposition: str
    effect_before: int
    effect_after: int
    exception_type: str
    exception_message: str
    evidence_ref: str

    @property
    def effect_observed(self) -> bool:
        return self.effect_after > self.effect_before


class RuntimeAdversarialEvidenceLedger:
    """Derive COI14 probe evidence from executed runtime controls.

    Callers provide an attack operation plus an effect counter. The ledger itself
    executes the attack, observes whether the material-effect counter changed,
    derives the defensive disposition from the observed runtime outcome, and
    hashes the complete event into an evidence reference. No caller may supply
    observed_disposition, effect_observed, or evidence_ref directly.
    """

    _CONTAINMENT = {
        "ADAPTER_UNAVAILABLE": "REPLAN",
        "EXECUTION_UNKNOWN": "RECONCILIATION_REQUIRED",
        "PARTIAL_EFFECT": "RECONCILIATION_REQUIRED",
        "CONCURRENT_RECEIPT_CONFLICT": "RECONCILIATION_REQUIRED",
        "TIMEOUT_DOUBLE_EXECUTION": "RECONCILIATION_REQUIRED",
    }

    def __init__(self) -> None:
        self._events: list[RuntimeAdversarialEvent] = []

    @property
    def events(self) -> tuple[RuntimeAdversarialEvent, ...]:
        return tuple(self._events)

    def execute_probe(
        self,
        *,
        probe_id: str,
        attack_class: str,
        attempted_action: str,
        attack: Callable[[], object],
        effect_counter: Callable[[], int],
    ) -> AdversarialProbe:
        before = int(effect_counter())
        exception_type = ""
        exception_message = ""
        try:
            attack()
        except Exception as exc:  # runtime observation is the evidence boundary
            exception_type = type(exc).__name__
            exception_message = str(exc)
        after = int(effect_counter())

        if after > before:
            disposition = "UNSAFE_EFFECT"
        elif exception_type:
            disposition = self._CONTAINMENT.get(attack_class, "DENIED")
        else:
            # An adversarial attempt that returns normally without a material
            # effect is still not accepted as a proven denial.
            disposition = "UNSAFE_NO_DENIAL"

        payload = {
            "probe_id": probe_id,
            "attack_class": attack_class,
            "attempted_action": attempted_action,
            "disposition": disposition,
            "effect_before": before,
            "effect_after": after,
            "exception_type": exception_type,
            "exception_message": exception_message,
        }
        evidence_ref = "runtime-evidence:" + sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        event = RuntimeAdversarialEvent(
            attack_class=attack_class,
            attempted_action=attempted_action,
            disposition=disposition,
            effect_before=before,
            effect_after=after,
            exception_type=exception_type,
            exception_message=exception_message,
            evidence_ref=evidence_ref,
        )
        self._events.append(event)
        return AdversarialProbe(
            probe_id=probe_id,
            attack_class=attack_class,
            attempted_action=attempted_action,
            observed_disposition=disposition,
            effect_observed=event.effect_observed,
            evidence_ref=evidence_ref,
        )
