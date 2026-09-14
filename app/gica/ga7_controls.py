from __future__ import annotations

from dataclasses import dataclass

from app.gica.ga7_ledger import Ga7Ledger

REQUIRED_LIMITS = (
    "MAX_DISCOVERY_CASES",
    "MAX_OCS_CALLS",
    "MAX_AGENT_RUNS",
    "MAX_MODEL_CALLS",
    "MAX_TOOL_CALLS",
    "MAX_RETRIES",
    "MAX_REPAIR_EPOCHS",
    "MAX_COST",
    "MAX_ELAPSED_TIME",
    "MAX_PIVOTS",
)

COUNTER_MAP = {
    "ocs": "MAX_OCS_CALLS",
    "agent": "MAX_AGENT_RUNS",
    "model": "MAX_MODEL_CALLS",
    "tool": "MAX_TOOL_CALLS",
    "retry": "MAX_RETRIES",
    "repair": "MAX_REPAIR_EPOCHS",
    "case": "MAX_DISCOVERY_CASES",
    "pivot": "MAX_PIVOTS",
}

SHARED_BUDGET_KEY = "GA7_SHARED_BUDGET"


@dataclass(frozen=True)
class Ga7BudgetEnvelope:
    MAX_DISCOVERY_CASES: int | None
    MAX_OCS_CALLS: int | None
    MAX_AGENT_RUNS: int | None
    MAX_MODEL_CALLS: int | None
    MAX_TOOL_CALLS: int | None
    MAX_RETRIES: int | None
    MAX_REPAIR_EPOCHS: int | None
    MAX_PARALLELISM: int
    MAX_RECURSION_DEPTH: int
    MAX_COST: float | None
    MAX_ELAPSED_TIME: float | None
    MAX_PIVOTS: int | None
    stop_rules_ref: str = ""

    def validate_profile(self) -> tuple[bool, str]:
        if self.MAX_PARALLELISM != 1:
            return False, "parallelism_denied"
        if self.MAX_RECURSION_DEPTH != 0:
            return False, "recursion_denied"
        for name in REQUIRED_LIMITS:
            value = getattr(self, name)
            if value is None:
                return False, f"unbound_{name}"
            if isinstance(value, (int, float)) and value < 0:
                return False, f"invalid_{name}"
        return True, "ok"


class Ga7BudgetControl:
    def __init__(self, envelope: Ga7BudgetEnvelope, ledger: Ga7Ledger, case_key: str) -> None:
        self.envelope = envelope
        self.ledger = ledger
        self.case_key = case_key
        self.store_key = envelope.stop_rules_ref or SHARED_BUDGET_KEY
        ok, reason = envelope.validate_profile()
        self.reason = reason
        self.active = ok
        if ok and not ledger.get_budget(self.store_key):
            ledger.put_budget(self.store_key, {name: 0 for name in COUNTER_MAP})

    def counters(self) -> dict:
        return self.ledger.get_budget(self.store_key)

    def allow(self, kind: str) -> tuple[bool, str]:
        if not self.active:
            return False, self.reason
        limit_name = COUNTER_MAP.get(kind)
        if limit_name is None:
            return False, "unknown_counter"
        used = self.counters().get(kind, 0)
        limit = getattr(self.envelope, limit_name)
        if used + 1 > limit:
            return False, "budget_exhausted"
        snapshot = self.counters()
        snapshot[kind] = used + 1
        self.ledger.put_budget(self.store_key, snapshot)
        return True, "allow"
