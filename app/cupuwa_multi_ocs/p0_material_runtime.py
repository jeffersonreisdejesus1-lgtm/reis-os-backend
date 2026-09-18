"""Bounded material runtime for the CUPUWA P0 mission.

This module produces an auditable material candidate in memory. It does not
grant authority, access external tools, or perform deployment effects.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import cast

from .p0_coi_ingress import MISSION_ID, discover_and_compose


def _digest(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=list,
    )
    return sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class WorkerReceipt:
    ocs_id: str
    capability: str
    status: str
    authority_granted: bool
    material_effect_claim: bool
    evidence_digest: str


@dataclass(frozen=True, slots=True)
class MaterialArtifact:
    mission_id: str
    artifact_type: str
    selected_ocs: tuple[str, ...]
    worker_receipts: tuple[WorkerReceipt, ...]
    artifact_digest: str


class P0MaterialOrchestrator:
    """Run one bounded, deterministic P0 material composition."""

    def execute(self) -> MaterialArtifact:
        composition = discover_and_compose()
        if composition["status"] != "COMPOSED":
            raise RuntimeError("cupuwa_p0_composition_not_ready")
        if composition["authority_granted"] or composition["effects_permitted"]:
            raise RuntimeError("cupuwa_p0_unauthorized_effects")

        raw_assignments = cast(list[dict[str, str]], composition["assignments"])
        assignments = tuple(raw_assignments)
        receipts = tuple(
            WorkerReceipt(
                ocs_id=assignment["ocs_id"],
                capability=assignment["capability"],
                status="OBSERVED",
                authority_granted=False,
                material_effect_claim=False,
                evidence_digest=_digest(
                    {
                        "mission_id": MISSION_ID,
                        "ocs_id": assignment["ocs_id"],
                        "capability": assignment["capability"],
                    }
                ),
            )
            for assignment in assignments
        )
        artifact_data: Mapping[str, object] = {
            "mission_id": MISSION_ID,
            "artifact_type": "CUPUWA_P0_GOVERNED_CANDIDATE",
            "selected_ocs": tuple(cast(tuple[str, ...], composition["selected_ocs"])),
            "worker_receipts": tuple(asdict(receipt) for receipt in receipts),
            "effects_permitted": False,
        }
        return MaterialArtifact(
            mission_id=MISSION_ID,
            artifact_type="CUPUWA_P0_GOVERNED_CANDIDATE",
            selected_ocs=tuple(cast(tuple[str, ...], composition["selected_ocs"])),
            worker_receipts=receipts,
            artifact_digest=_digest(artifact_data),
        )
