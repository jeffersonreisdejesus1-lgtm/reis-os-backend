from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.command.application import list_ocs_profiles
from app.command.instance_views import CommandInstanceViews, InstanceFilter
from app.command.read_models import CommandReadModels
from app.governance_refactor.projections import GovernanceCommandViews


@dataclass(frozen=True, slots=True)
class CommandProductSources:
    command_event_store_path: str | Path
    ocs_instance_store_path: str | Path
    governance_candidate_store_path: str | Path


class CommandProductViews:
    """Read-only B10 product projection over existing canonical/bounded stores.

    This class deliberately owns no persistence. It composes already-established
    read models and preserves `COMMAND != SOURCE_OF_TRUTH`.
    """

    def __init__(self, sources: CommandProductSources) -> None:
        self._sources = sources

    def cockpit(self, *, organization_id: str) -> dict[str, Any]:
        command = CommandReadModels(self._sources.command_event_store_path)
        instances = CommandInstanceViews(self._sources.ocs_instance_store_path)
        governance = GovernanceCommandViews(
            self._sources.governance_candidate_store_path
        )

        instance_page = instances.list_instances(
            organization_id=organization_id,
            filters=InstanceFilter(),
            cursor=None,
            limit=100,
        )
        recovery = instances.recovery_center(
            organization_id=organization_id,
            filters=InstanceFilter(),
            cursor=None,
            limit=100,
        )
        capabilities = governance.capability_health(
            organization_id=organization_id
        )
        snapshot = command.snapshot()

        ocs_profiles = list_ocs_profiles()
        ocs_items = [
            {
                "slug": item.slug,
                "ocs_id": item.ocs_id,
                "identity": item.identity,
                "specialty": item.specialty,
                "support_capabilities": list(item.support_capabilities),
                "allowed_action_classes": list(item.allowed_action_classes),
                "denied_action_classes": list(item.denied_action_classes),
                "authority_envelope_ref": item.authority_envelope_ref,
                "namespaces": item.namespaces.model_dump(),
                "source": item.source.model_dump(),
            }
            for item in ocs_profiles.items
        ]

        return {
            "product": {
                "id": "REIS_OS_COMMAND_B10",
                "surface": "CONTROL_PLANE",
                "mode": "projection_plus_bounded_controls",
            },
            "institution": snapshot.institution,
            "ocs": {
                "count": len(ocs_items),
                "items": ocs_items,
            },
            "operations": list(snapshot.operations.values()),
            "gates": list(snapshot.gates.values()),
            "evidence": list(snapshot.evidence.values()),
            "system_health": snapshot.system_health,
            "maps": list(snapshot.maps.values()),
            "instances": instance_page,
            "recovery_center": recovery,
            "capabilities": capabilities,
            "epistemic_boundary": {
                "command_is_source_of_truth": False,
                "command_is_promotion_decider": False,
                "requested_is_executed": False,
                "executed_is_verified": False,
                "verified_is_assured": False,
                "unknown_is_zero": False,
                "ui_creates_authority": False,
            },
        }
