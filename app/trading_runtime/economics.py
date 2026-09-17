from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from threading import Lock
from uuid import uuid4


@dataclass(frozen=True)
class BudgetPolicy:
    daily: Decimal
    monthly: Decimal
    run: Decimal
    signal: Decimal
    cycle_call_limit: int
    strong_model_limit: int


@dataclass
class Reservation:
    reservation_id: str
    expected_cost: Decimal
    strong: bool = False
    committed: bool = False


@dataclass
class EconomicGovernor:
    policy: BudgetPolicy
    spent_daily: Decimal = Decimal("0")
    spent_monthly: Decimal = Decimal("0")
    spent_run: Decimal = Decimal("0")
    calls_this_cycle: int = 0
    strong_calls_today: int = 0
    _reserved: Decimal = Decimal("0")
    _reservations: dict[str, Reservation] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def reserve(self, expected_cost: Decimal, *, strong: bool = False) -> Reservation | None:
        with self._lock:
            if expected_cost < 0 or expected_cost > self.policy.signal:
                return None
            if self.calls_this_cycle >= self.policy.cycle_call_limit:
                return None
            outstanding_strong = sum(
                1 for reservation in self._reservations.values() if reservation.strong
            )
            if (
                strong
                and self.strong_calls_today + outstanding_strong
                >= self.policy.strong_model_limit
            ):
                return None
            projected = self._reserved + expected_cost
            if self.spent_daily + projected > self.policy.daily:
                return None
            if self.spent_monthly + projected > self.policy.monthly:
                return None
            if self.spent_run + projected > self.policy.run:
                return None
            reservation = Reservation(str(uuid4()), expected_cost, strong=strong)
            self._reservations[reservation.reservation_id] = reservation
            self._reserved += expected_cost
            self.calls_this_cycle += 1
            return reservation

    def reconcile(self, reservation_id: str, actual_cost: Decimal, *, strong: bool = False) -> bool:
        with self._lock:
            reservation = self._reservations.get(reservation_id)
            if reservation is None:
                return False
            if actual_cost < 0 or strong != reservation.strong:
                return False
            self._reservations.pop(reservation_id)
            self._reserved -= reservation.expected_cost
            self.spent_daily += actual_cost
            self.spent_monthly += actual_cost
            self.spent_run += actual_cost
            if reservation.strong:
                self.strong_calls_today += 1
            reservation.committed = True
            return True

    def rollback(self, reservation_id: str) -> bool:
        with self._lock:
            reservation = self._reservations.pop(reservation_id, None)
            if reservation is None:
                return False
            self._reserved -= reservation.expected_cost
            return True
