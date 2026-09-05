from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.command.application import OCS_SLUGS, SLUG_TO_OCS_ID
from app.command.event_store import CommandEventStore
from app.command.events import Freshness
from app.profile_bindings.profiles import PROFILE_VERSION, PROFILES


@dataclass(frozen=True)
class OCSDossier:
    slug: str
    ocs_id: str
    identity: str
    capability: tuple[str, ...]
    authority: dict[str, Any]
    expertise: str
    current_state: dict[str, Any]
    evidence_refs: tuple[str, ...]
    freshness: Freshness
    source: dict[str, str]
    version: str
    institutional_relations: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "ocs_id": self.ocs_id,
            "identity": self.identity,
            "capability": list(self.capability),
            "authority": self.authority,
            "expertise": self.expertise,
            "current_state": self.current_state,
            "evidence_refs": list(self.evidence_refs),
            "freshness": self.freshness.value,
            "source": self.source,
            "version": self.version,
            "institutional_relations": self.institutional_relations,
        }


class CommandDossierService:
    def __init__(self, database_path: str | Path) -> None:
        self._database_path = database_path

    def list(self) -> list[dict[str, Any]]:
        return [self._build(ocs_id).as_dict() for ocs_id in OCS_SLUGS]

    def get(self, slug: str) -> dict[str, Any] | None:
        ocs_id = SLUG_TO_OCS_ID.get(slug.casefold())
        return None if ocs_id is None else self._build(ocs_id).as_dict()

    def _build(self, ocs_id: str) -> OCSDossier:
        profile = PROFILES[ocs_id]
        events = [
            event
            for event in CommandEventStore(self._database_path).read_all()
            if event.ocs_id == ocs_id
        ]
        latest = events[-1] if events else None
        evidence_refs = tuple(
            dict.fromkeys(ref for event in events for ref in event.evidence_refs)
        )
        if latest is None:
            current_state: dict[str, Any] = {
                "status": "unknown",
                "reason": "no_material_runtime_event",
            }
            freshness = Freshness.UNKNOWN
            runtime_source = "none"
            runtime_version = "none"
        else:
            current_state = {
                "status": "observed",
                "event_type": latest.event_type,
                "event_id": latest.event_id,
                "sequence": latest.sequence,
                "payload": latest.payload,
            }
            freshness = latest.freshness
            runtime_source = latest.source
            runtime_version = latest.source_version
        return OCSDossier(
            slug=OCS_SLUGS[ocs_id],
            ocs_id=ocs_id,
            identity=profile.identity,
            capability=profile.support_capabilities,
            authority={
                "authority_envelope_ref": profile.authority_envelope_ref,
                "allowed_action_classes": list(profile.allowed_action_classes),
                "denied_action_classes": list(profile.denied_action_classes),
            },
            expertise=profile.specialty,
            current_state=current_state,
            evidence_refs=evidence_refs,
            freshness=freshness,
            source={
                "profile": "app/profile_bindings/profiles.py",
                "runtime": runtime_source,
                "runtime_version": runtime_version,
            },
            version=f"profile:{PROFILE_VERSION};runtime:{runtime_version}",
            institutional_relations={
                "handoff_policy": profile.handoff_policy,
                "kernel_interface_ref": profile.kernel_interface_ref,
                "state_namespace": profile.state_namespace,
                "memory_namespace": profile.memory_namespace,
            },
        )
