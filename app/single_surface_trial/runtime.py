from __future__ import annotations

from typing import Any

from .store import BindingReceipt, HandoffReceipt, TrialStore


class Binder:
    def __init__(self, store: TrialStore) -> None:
        self._store = store

    def bind(
        self,
        mission_id: str,
        ocs_id: str,
        instance_id: str,
        *,
        authority_ref: str,
        activate_if_empty: bool = False,
    ) -> BindingReceipt:
        return self._store.bind(
            mission_id,
            ocs_id,
            instance_id,
            authority_ref=authority_ref,
            activate_if_empty=activate_if_empty,
        )


class HandoffQueue:
    def __init__(self, store: TrialStore) -> None:
        self._store = store

    def issue(
        self,
        mission_id: str,
        *,
        route_id: str,
        target_instance_id: str,
        target_ocs_id: str,
        envelope: dict[str, Any],
    ) -> str:
        return self._store.issue_handoff(
            mission_id,
            route_id=route_id,
            target_instance_id=target_instance_id,
            target_ocs_id=target_ocs_id,
            envelope=envelope,
        )

    def accept(self, mission_id: str, handoff_id: str) -> HandoffReceipt:
        return self._store.accept_handoff(mission_id, handoff_id)


class RuntimeLifecycle:
    def __init__(self, store: TrialStore) -> None:
        self._store = store

    def recover(
        self,
        mission_id: str,
        *,
        ocs_id: str,
        successor_instance_id: str,
        authority_ref: str,
    ) -> BindingReceipt:
        return self._store.recover(
            mission_id,
            ocs_id=ocs_id,
            successor_instance_id=successor_instance_id,
            authority_ref=authority_ref,
        )


class MissionController:
    """Advances only an explicitly allowlisted, fully receipted handoff."""

    def __init__(self, store: TrialStore) -> None:
        self._store = store
        self._queue = HandoffQueue(store)

    def handoff(
        self,
        mission_id: str,
        *,
        route_id: str,
        target_instance_id: str,
        target_ocs_id: str,
        envelope: dict[str, Any],
    ) -> HandoffReceipt:
        handoff_id = self._queue.issue(
            mission_id,
            route_id=route_id,
            target_instance_id=target_instance_id,
            target_ocs_id=target_ocs_id,
            envelope=envelope,
        )
        return self._queue.accept(mission_id, handoff_id)
