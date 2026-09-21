from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.cupuwa_multi_ocs.contracts import ContractViolation, MissionContract
from app.cupuwa_multi_ocs.p0_coi_ingress import discover_and_compose
from app.cupuwa_skills.coi_bridge import execute_coi_skill
from app.cupuwa_skills.loader import SkillLoader
from app.cupuwa_skills.registry import SkillDescriptor, SkillRegistry
from app.profile_bindings.canonical_registry import (
    CANONICAL_OCS_REGISTRY,
    validate_canonical_registry,
)

EVIDENCE_DIR = Path("/tmp/w05-d04-evidence")
OCS_IDS = tuple(sorted(CANONICAL_OCS_REGISTRY))


def _mission(
    capability: str,
    authority_ref: str = "authority://d04/probe",
) -> MissionContract:
    return MissionContract(
        mission_id="CUPUWA-D04-OCS-PROBE",
        product="CUPUWA",
        increment_id="D04",
        bound_object="ocs-individual-qualification",
        bound_head="ad2d3036a669225a730ecc9c932d6acb69bd3ae5",
        requested_outcome="bounded local skill receipt",
        constraints=("no_external_effect", "no_authority_expansion"),
        authority_ref=authority_ref,
        required_capabilities=(capability,),
        evidence_policy="receipt",
        completion_policy="qualified",
    )


def _composition_index() -> dict[str, list[str]]:
    composition = discover_and_compose()
    assigned: dict[str, list[str]] = {}
    assignments = composition.get("assignments")
    if not isinstance(assignments, list):
        return assigned
    for item in assignments:
        if not isinstance(item, dict):
            continue
        ocs_id = item.get("ocs_id")
        capability = item.get("capability")
        if isinstance(ocs_id, str) and isinstance(capability, str):
            assigned.setdefault(ocs_id, []).append(capability)
    return assigned


def test_d04_registry_identity_is_not_execution_proof() -> None:
    validate_canonical_registry()
    assert len(OCS_IDS) == 72
    for ocs_id in OCS_IDS:
        profile = CANONICAL_OCS_REGISTRY[ocs_id]
        assert profile.ocs_id == ocs_id
        assert profile.identity.startswith("identity://")
        assert profile.authority_envelope_ref.startswith("authority://")
        assert profile.support_capabilities
        assert "authority_creation" in profile.denied_action_classes or (
            "authority_creation" not in profile.allowed_action_classes
        )


def test_d04_individual_probes_are_sequential_and_recorded() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    composition = discover_and_compose()
    assigned = _composition_index()
    rows: list[dict[str, Any]] = []

    for ocs_id in OCS_IDS:
        profile = CANONICAL_OCS_REGISTRY[ocs_id]
        composed_caps = assigned.get(ocs_id, [])
        if composed_caps:
            primary_cap = composed_caps[0]
        else:
            primary_cap = profile.support_capabilities[0]
        row: dict[str, Any] = {
            "ocs_id": ocs_id,
            "identity": profile.identity,
            "profile": profile.specialty,
            "physiology": profile.csp_ref,
            "capability": primary_cap,
            "authority": profile.authority_envelope_ref,
            "runtime_entrypoint": "execute_coi_skill",
            "composed_in_coi": bool(composed_caps),
            "probes": {},
            "classification": "NOT_PROVEN",
        }

        row["probes"]["p01_identity"] = "PASS"
        declared = primary_cap in profile.support_capabilities or bool(
            composed_caps
        )
        row["probes"]["p02_capability_declared"] = "PASS" if declared else "FAIL"
        envelope_ok = profile.authority_envelope_ref.startswith("authority://")
        row["probes"]["p03_authority_envelope"] = "PASS" if envelope_ok else "FAIL"
        row["probes"]["p04_coi_composition"] = (
            "PASS" if composed_caps else "NOT_PROVEN"
        )

        if not composed_caps:
            row["probes"]["p05_runtime_entry"] = "NOT_PROVEN"
            row["probes"]["p06_controlled_execution"] = "NOT_PROVEN"
            row["probes"]["p07_receipt"] = "NOT_PROVEN"
            row["probes"]["p08_no_authority"] = "NOT_PROVEN"
            row["probes"]["p09_out_of_scope"] = "NOT_PROVEN"
            row["probes"]["p10_missing_executor"] = "NOT_PROVEN"
            row["probes"]["p11_replay"] = "NOT_PROVEN"
            row["classification"] = "PARTIAL"
            row["note"] = (
                "identity/authority declared; no COI assignment; "
                "execution not attempted"
            )
            rows.append(row)
            continue

        registry = SkillRegistry(
            [
                SkillDescriptor(
                    skill_id=f"d04-{ocs_id}",
                    version="1.0.0",
                    capabilities=frozenset({primary_cap}),
                    compatible_ocs=frozenset({ocs_id}),
                )
            ]
        )
        def _procedure(
            payload: dict[str, Any],
            bound: str = ocs_id,
        ) -> dict[str, Any]:
            return {"ocs": bound, "n": payload.get("n")}

        loader = SkillLoader({f"d04-{ocs_id}": _procedure})
        mission = _mission(primary_cap)

        first = execute_coi_skill(
            registry,
            loader,
            mission,
            capability=primary_cap,
            payload={"n": 1},
        )
        assert first.selected_ocs == ocs_id
        assert first.receipt.status == "SUCCESS"
        row["probes"]["p05_runtime_entry"] = "PASS"
        row["probes"]["p06_controlled_execution"] = "PASS"
        row["probes"]["p07_receipt"] = first.receipt.result_digest
        row["receipt"] = {
            "skill_id": first.receipt.skill_id,
            "status": first.receipt.status,
            "digest": first.receipt.result_digest,
            "composition_receipt": first.composition_receipt,
            "selected_ocs": first.selected_ocs,
        }

        unauthorized = _mission(primary_cap)
        object.__setattr__(unauthorized, "authority_ref", None)
        with pytest.raises(ContractViolation, match="mission_authority_required"):
            execute_coi_skill(
                registry,
                loader,
                unauthorized,
                capability=primary_cap,
                payload={"n": 1},
            )
        row["probes"]["p08_no_authority"] = "PASS"

        with pytest.raises(ContractViolation, match="capability_not_bound_to_mission"):
            execute_coi_skill(
                registry,
                loader,
                mission,
                capability="capability_outside_mission_scope",
                payload={},
            )
        row["probes"]["p09_out_of_scope"] = "PASS"

        empty_loader = SkillLoader({})
        with pytest.raises(LookupError, match="skill_procedure_not_available"):
            execute_coi_skill(
                registry,
                empty_loader,
                mission,
                capability=primary_cap,
                payload={"n": 1},
            )
        row["probes"]["p10_missing_executor"] = "PASS"

        second = execute_coi_skill(
            registry,
            loader,
            mission,
            capability=primary_cap,
            payload={"n": 1},
        )
        assert second.receipt.result_digest == first.receipt.result_digest
        assert second.selected_ocs == first.selected_ocs
        row["probes"]["p11_replay"] = "PASS"
        row["classification"] = "PARTIAL"
        row["note"] = (
            "COI-routed local procedure only; not the OCS body; "
            "not a material CUPUWA effect"
        )
        rows.append(row)

    payload = {
        "procedure": "CUPUWA-OCS-INDIVIDUAL-QUALIFICATION-001",
        "increment": "D04",
        "bound_head": "ad2d3036a669225a730ecc9c932d6acb69bd3ae5",
        "composition_status": composition.get("status"),
        "denominator": 72,
        "rows": rows,
    }
    artifact = EVIDENCE_DIR / "d04-ocs-probe-matrix.json"
    artifact.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    proven = [row for row in rows if row["classification"] == "PROVEN"]
    assert not proven
    assert len(rows) == 72
    assert all(row["classification"] in {"PARTIAL", "NOT_PROVEN"} for row in rows)
