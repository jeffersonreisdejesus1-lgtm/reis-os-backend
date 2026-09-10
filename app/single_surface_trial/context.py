from __future__ import annotations

from typing import Any

from .contracts import TrialHold, memory_namespace


class ContextBuilder:
    def build(
        self,
        *,
        mission_id: str,
        target_ocs_id: str,
        mission_required_context: dict[str, Any],
        canonical_state: dict[str, Any],
        handoff_envelope: dict[str, Any],
        target_memory_refs: tuple[str, ...],
        source_transient_context: dict[str, Any] | None = None,
        source_private_memory_refs: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        expected_memory_prefix = memory_namespace(mission_id, target_ocs_id)
        if any(
            not ref.startswith(expected_memory_prefix) for ref in target_memory_refs
        ):
            raise TrialHold("target_memory_namespace_invalid")
        if source_private_memory_refs:
            raise TrialHold("cross_ocs_private_memory_import_forbidden")
        _ = source_transient_context
        return {
            "mission_required_context": mission_required_context,
            "canonical_state": canonical_state,
            "handoff_envelope": handoff_envelope,
            "target_memory_refs": target_memory_refs,
        }
