from __future__ import annotations

from dataclasses import dataclass

from .contracts import HandoffAcceptance, HandoffReceipt, LPEUpdate


@dataclass(frozen=True)
class PIActivation:
    pi_id: str
    ocs: str
    active: bool


class PIActivationRegistry:
    def __init__(self) -> None:
        self._items: dict[str, PIActivation] = {}

    def set(self, activation: PIActivation) -> None:
        self._items[activation.pi_id] = activation

    def is_active(self, pi_id: str, ocs: str) -> bool:
        item = self._items.get(pi_id)
        return item is not None and item.ocs == ocs and item.active


class HandoffRouter:
    def close(
        self,
        *,
        receipt_id: str,
        source_ocs: str,
        target_ocs: str,
        state_ref: str,
        context_refs: tuple[str, ...] = (),
        evidence_refs: tuple[str, ...] = (),
        source_authority_ref: str = "",
    ) -> HandoffReceipt:
        return HandoffReceipt(
            receipt_id=receipt_id,
            source_ocs=source_ocs,
            target_ocs=target_ocs,
            state_ref=state_ref,
            authority_transferred=False,
            context_refs=context_refs,
            evidence_refs=evidence_refs,
            source_authority_ref=source_authority_ref,
        )

    def accept(
        self,
        receipt: HandoffReceipt,
        *,
        receiver_ocs: str,
    ) -> HandoffAcceptance:
        if receiver_ocs != receipt.target_ocs:
            raise ValueError("handoff_receiver_mismatch")
        return HandoffAcceptance(
            handoff_id=receipt.handoff_id,
            receiver_ocs=receiver_ocs,
            context_refs=receipt.context_refs,
            evidence_refs=receipt.evidence_refs,
            executable_authority_ref=None,
        )


class LPEPort:
    def validate(self, update: LPEUpdate) -> None:
        if update.changes_authority:
            raise ValueError("lpe_authority_expansion_prohibited")
        if update.changes_constitution:
            raise ValueError("lpe_constitution_mutation_prohibited")
        source = update.imports_autobiography_from_ocs
        if source is not None and source != update.ocs:
            raise ValueError("cross_ocs_autobiography_import_prohibited")
