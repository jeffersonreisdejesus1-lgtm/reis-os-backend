from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


class ConfigManager:
    """Stores non-secret config; secret-like keys must use external references."""

    _secret_terms = ("SECRET", "TOKEN", "PASSWORD", "API_KEY", "PRIVATE_KEY")

    def __init__(self) -> None:
        self._values: dict[str, str] = {}
        self._lock = Lock()

    def set(self, key: str, value: str) -> None:
        upper = key.upper()
        if any(term in upper for term in self._secret_terms) and not value.startswith("ref://"):
            raise ValueError("secret material must be referenced, not stored")
        with self._lock:
            self._values[key] = value

    def snapshot(self) -> dict[str, str]:
        with self._lock:
            return dict(self._values)


class FeatureFlagManager:
    def __init__(self) -> None:
        self._flags: dict[str, bool] = {}
        self._lock = Lock()

    def set(self, name: str, enabled: bool) -> None:
        with self._lock:
            self._flags[name] = enabled

    def enabled(self, name: str) -> bool:
        with self._lock:
            return self._flags.get(name, False)


@dataclass(frozen=True)
class MigrationPlan:
    migration_id: str
    up: str
    down: str


class MigrationGate:
    def validate(self, plan: MigrationPlan | None) -> tuple[bool, str | None]:
        if plan is None:
            return True, None
        if not plan.up.strip():
            return False, "MIGRATION_UP_MISSING"
        if not plan.down.strip():
            return False, "MIGRATION_ROLLBACK_MISSING"
        destructive = ("DROP TABLE", "DROP COLUMN", "TRUNCATE ")
        upper = plan.up.upper()
        if any(token in upper for token in destructive) and "-- ALLOW_DESTRUCTIVE" not in upper:
            return False, "DESTRUCTIVE_MIGRATION_UNACKNOWLEDGED"
        return True, None


@dataclass(frozen=True)
class PerformancePolicy:
    max_p95_ms: float = 750.0
    max_error_rate_pct: float = 1.0


class PerformanceGate:
    def __init__(self, policy: PerformancePolicy | None = None) -> None:
        self.policy = policy or PerformancePolicy()

    def validate(self, p95_ms: float, error_rate_pct: float) -> tuple[bool, tuple[str, ...]]:
        reasons: list[str] = []
        if p95_ms < 0 or p95_ms > self.policy.max_p95_ms:
            reasons.append("P95_LATENCY_BREACH")
        if error_rate_pct < 0 or error_rate_pct > self.policy.max_error_rate_pct:
            reasons.append("ERROR_RATE_BREACH")
        return not reasons, tuple(reasons)


@dataclass(frozen=True)
class SLOPolicy:
    availability_target_pct: float = 99.0
    p95_latency_target_ms: float = 750.0
    error_budget_pct: float = 1.0

    def as_dict(self) -> dict[str, float]:
        return {
            "availability_target_pct": self.availability_target_pct,
            "p95_latency_target_ms": self.p95_latency_target_ms,
            "error_budget_pct": self.error_budget_pct,
        }
