from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from json import dumps

from .identity import (
    ActiveIdentityBinding,
    IdentityKernelGuard,
    IdentityRecheckTrigger,
)


@dataclass(frozen=True)
class HandoffIdentityReceipt:
    handoff_id: str
    sender_ocs_canonical_name: str
    sender_ocs_id: str
    sender_host: str
    receiver_ocs_canonical_name: str
    receiver_ocs_id: str
    receiver_host_if_known: str | None
    object_ref: str
    authorized_next_scope: tuple[str, ...]
    authority_ref: str
    sender_identity_binding_hash: str
    identity_transfer: bool = False
    authority_transfer: bool = False
    cross_ocs_memory_import: bool = False


@dataclass(frozen=True)
class HandoffIdentityAcceptance:
    handoff_id: str
    receiver_binding: ActiveIdentityBinding
    authorized_next_scope: tuple[str, ...]
    source_authority_ref: str
    executable_authority_ref: None = None


class HandoffIdentityGate:
    @staticmethod
    def _binding_hash(binding: ActiveIdentityBinding) -> str:
        raw = asdict(binding)
        raw["status"] = binding.status.value
        canonical = dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return sha256(canonical.encode("utf-8")).hexdigest()

    def issue(
        self,
        *,
        guard: IdentityKernelGuard,
        run_id: str,
        handoff_id: str,
        sender_ocs: str,
        sender_host: str,
        receiver_ocs: str,
        receiver_host_if_known: str | None,
        object_ref: str,
        authorized_next_scope: tuple[str, ...],
        authority_ref: str,
    ) -> HandoffIdentityReceipt:
        if not handoff_id or not object_ref or not authorized_next_scope:
            raise ValueError("handoff_identity_fields_required")
        binding = guard.require_valid(
            run_id=run_id,
            expected_ocs=sender_ocs,
            trigger=IdentityRecheckTrigger.PRE_HANDOFF,
            host=sender_host,
        )
        receipt = HandoffIdentityReceipt(
            handoff_id=handoff_id,
            sender_ocs_canonical_name=binding.ocs_canonical_name,
            sender_ocs_id=binding.ocs_id,
            sender_host=binding.host,
            receiver_ocs_canonical_name=receiver_ocs,
            receiver_ocs_id=receiver_ocs,
            receiver_host_if_known=receiver_host_if_known,
            object_ref=object_ref,
            authorized_next_scope=authorized_next_scope,
            authority_ref=authority_ref,
            sender_identity_binding_hash=self._binding_hash(binding),
        )
        guard.audit_log.append(
            "HANDOFF_IDENTITY_RECEIPT",
            binding,
            details={
                "handoff_id": handoff_id,
                "receiver_ocs": receiver_ocs,
                "object_ref": object_ref,
                "authorized_next_scope": authorized_next_scope,
                "identity_transfer": False,
                "authority_transfer": False,
                "cross_ocs_memory_import": False,
            },
        )
        return receipt

    def accept(
        self,
        receipt: HandoffIdentityReceipt,
        *,
        receiver_guard: IdentityKernelGuard,
        receiver_run_id: str,
        receiver_ocs: str,
        receiver_host: str,
        session_context: str,
    ) -> HandoffIdentityAcceptance:
        if receipt.identity_transfer:
            raise ValueError("handoff_identity_transfer_prohibited")
        if receipt.authority_transfer:
            raise ValueError("handoff_authority_transfer_prohibited")
        if receipt.cross_ocs_memory_import:
            raise ValueError("cross_ocs_memory_import_prohibited")
        if receiver_ocs != receipt.receiver_ocs_id:
            raise ValueError("handoff_receiver_mismatch")
        if (
            receipt.receiver_host_if_known is not None
            and receiver_host != receipt.receiver_host_if_known
        ):
            raise ValueError("handoff_receiver_host_mismatch")
        if not receipt.sender_ocs_id or not receipt.sender_identity_binding_hash:
            raise ValueError("handoff_sender_identity_binding_required")

        # The receiver obtains its own binding. Sender identity, authority and memory
        # are never imported as receiver identity/authority/memory.
        receiver_binding = receiver_guard.bind_active_identity(
            run_id=receiver_run_id,
            ocs_id=receiver_ocs,
            host=receiver_host,
            session_context=session_context,
        )
        receiver_guard.audit_log.append(
            "HANDOFF_ACCEPTED_WITH_NEW_IDENTITY_BINDING",
            receiver_binding,
            details={
                "handoff_id": receipt.handoff_id,
                "sender_ocs": receipt.sender_ocs_id,
                "object_ref": receipt.object_ref,
                "source_authority_ref": receipt.authority_ref,
                "executable_authority_ref": None,
            },
        )
        return HandoffIdentityAcceptance(
            handoff_id=receipt.handoff_id,
            receiver_binding=receiver_binding,
            authorized_next_scope=receipt.authorized_next_scope,
            source_authority_ref=receipt.authority_ref,
            executable_authority_ref=None,
        )
