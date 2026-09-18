from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class TrialHold(RuntimeError):
    """Fail-closed trial boundary."""


class MissionStatus(StrEnum):
    PREPARED = "prepared"
    BUILD_VERIFICATION = "build_verification"
    HOLD = "hold"
    IMPLEMENTATION_COMPLETE = "implementation_complete"


class BindingStatus(StrEnum):
    BOUND = "bound"
    ACTIVE = "active"
    QUIESCENT = "quiescent"
    FENCED = "fenced"


class Decision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    HOLD = "hold"


@dataclass(frozen=True, slots=True)
class RouteSpec:
    route_id: str
    source_ocs: str | None
    target_ocs: str | None
    source_actor_class: str | None = None
    target_actor: str | None = None


L2_ROUTES: dict[str, RouteSpec] = {
    "L2-SINGLE-SURFACE-DEDALA-TO-SOFIA-PLAN-001": RouteSpec(
        route_id="L2-SINGLE-SURFACE-DEDALA-TO-SOFIA-PLAN-001",
        source_ocs="DÉDALA",
        target_ocs="SOFIA",
    ),
    "L2-SINGLE-SURFACE-SOFIA-TO-SYNESIS-ASSURANCE-001": RouteSpec(
        route_id="L2-SINGLE-SURFACE-SOFIA-TO-SYNESIS-ASSURANCE-001",
        source_ocs="SOFIA",
        target_ocs="SÝNESIS",
    ),
    "L2-SINGLE-SURFACE-IMPLEMENTER-TO-SYNESIS-IMPLEMENTATION-ASSURANCE-001": RouteSpec(
        route_id=(
            "L2-SINGLE-SURFACE-IMPLEMENTER-TO-SYNESIS-"
            "IMPLEMENTATION-ASSURANCE-001"
        ),
        source_ocs=None,
        target_ocs="SÝNESIS",
        source_actor_class="AUTHORIZED_IMPLEMENTER",
    ),
    "L2-SINGLE-SURFACE-SYNESIS-TO-FOUNDER-TRIAL-GATE-001": RouteSpec(
        route_id="L2-SINGLE-SURFACE-SYNESIS-TO-FOUNDER-TRIAL-GATE-001",
        source_ocs="SÝNESIS",
        target_ocs=None,
        target_actor="FOUNDER",
    ),
}


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def state_namespace(mission_id: str, ocs_id: str) -> str:
    return f"trial:{mission_id}:{ocs_id}:state:"


def memory_namespace(mission_id: str, ocs_id: str) -> str:
    return f"trial:{mission_id}:{ocs_id}:memory:"
