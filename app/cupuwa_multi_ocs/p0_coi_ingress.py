from __future__ import annotations

import json
from hashlib import sha256

from app.profile_bindings.canonical_registry import (
    CANONICAL_OCS_REGISTRY,
    validate_canonical_registry,
)

MISSION_ID = "CUPUWA-P0-CORE-FINANCE-MATERIAL-001"
MISSION_CONTRACT = "docs/cupuwa/CUPUWA-P0-CORE-FINANCE-MATERIAL-MISSION-001.md"
POLICY_VERSION = "CUPUWA-P0-001"

REQUIRED_CAPABILITIES = (
    "product", "requirements", "domain", "money", "ledger", "precision",
    "mobile_architecture", "state", "database", "persistence", "migrations",
    "offline_first", "android", "kotlin", "android_platform", "gradle",
    "ux", "ui", "accessibility", "privacy", "security",
    "unit_tests", "integration_tests", "e2e", "adversarial",
    "ci_cd", "build", "artifacts", "local_ai", "mobile_ai",
)

def _digest(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=list,
    )
    return sha256(payload.encode()).hexdigest()

def discover_and_compose() -> dict[str, object]:
    validate_canonical_registry()
    assignments: list[dict[str, str]] = []
    selected: set[str] = set()
    missing: list[str] = []
    for capability in REQUIRED_CAPABILITIES:
        candidates = sorted(
            p.ocs_id for p in CANONICAL_OCS_REGISTRY.values()
            if capability in p.support_capabilities
        )
        if not candidates:
            missing.append(capability)
            continue
        chosen = candidates[0]
        selected.add(chosen)
        assignments.append({"capability": capability, "ocs_id": chosen})
    status = "HOLD" if missing else "COMPOSED"
    payload = {
        "mission_id": MISSION_ID,
        "mission_contract": MISSION_CONTRACT,
        "policy_version": POLICY_VERSION,
        "pool_size": len(CANONICAL_OCS_REGISTRY),
        "required_capabilities": REQUIRED_CAPABILITIES,
        "assignments": assignments,
        "selected_ocs": sorted(selected),
        "missing_capabilities": missing,
        "authority_granted": False,
        "effects_permitted": False,
        "status": status,
    }
    payload["discovery_receipt"] = _digest(
        {"mission_id": MISSION_ID, "assignments": assignments, "missing": missing}
    )
    payload["composition_receipt"] = _digest(payload)
    return payload

if __name__ == "__main__":
    print(
        json.dumps(
            discover_and_compose(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )
