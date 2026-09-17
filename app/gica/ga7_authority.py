from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.gica.ga7_ledger import Ga7Ledger
from app.gica.ga7_types import (
    ALLOWED_OPERATION,
    EXPECTED_GATE,
    EXPECTED_POLICY,
    EXPECTED_PROGRAM,
    Ga7DiscoveryCaseInput,
    Ga7EpistemicClass,
    Ga7ReceiptType,
)

DENIED_OPERATIONS = frozenset(
    {
        "GA7_ENTRY",
        "GA8_ENTRY",
        "MERGE",
        "PROMOTION",
        "FOUNDER_ACTION",
        "SELF_PROMOTION",
        "AUTHORITY_EXPANSION",
        "GATE_TRANSITION",
    }
)


@dataclass(frozen=True)
class Ga7AuthorityToken:
    program_id: str
    gate_id: str
    bound_head: str
    object_version: str
    policy_version: str
    operation: str
    issuer: str
    verifier: str
    issued_at: datetime
    expires_at: datetime
    scope: str


@dataclass(frozen=True)
class Ga7AuthorityReceipt:
    admitted: bool
    reason: str
    operation: str


class Ga7Authority:
    def admit(
        self,
        case: Ga7DiscoveryCaseInput,
        token: Ga7AuthorityToken | None,
        ledger: Ga7Ledger | None = None,
        now: datetime | None = None,
    ) -> Ga7AuthorityReceipt:
        moment = now or datetime.now(UTC)
        if token is None:
            receipt = Ga7AuthorityReceipt(False, "absent_authority", "")
            self._record(ledger, case, receipt)
            return receipt
        if token.program_id != EXPECTED_PROGRAM or case.program_id != EXPECTED_PROGRAM:
            return self._deny(ledger, case, "wrong_program", token.operation)
        if token.gate_id != EXPECTED_GATE or case.gate_id != EXPECTED_GATE:
            return self._deny(ledger, case, "wrong_gate", token.operation)
        if token.bound_head != case.bound_head:
            return self._deny(ledger, case, "wrong_bound_head", token.operation)
        if (
            token.policy_version != EXPECTED_POLICY
            or case.policy_version != EXPECTED_POLICY
        ):
            return self._deny(ledger, case, "wrong_policy", token.operation)
        if token.object_version != case.object_version:
            return self._deny(ledger, case, "wrong_object_version", token.operation)
        if token.operation in DENIED_OPERATIONS:
            return self._deny(ledger, case, "forbidden_operation", token.operation)
        if token.operation != ALLOWED_OPERATION:
            return self._deny(ledger, case, "wrong_scope", token.operation)
        if token.issuer != "NOESIS-AUTHORITY" or token.verifier != "SYNESIS-VERIFIER":
            return self._deny(
                ledger, case, "untrusted_issuer_or_verifier", token.operation
            )
        if token.expires_at <= moment or token.issued_at > moment:
            return self._deny(ledger, case, "stale_authority", token.operation)
        if token.scope != case.authority_scope:
            return self._deny(ledger, case, "wrong_scope", token.operation)
        receipt = Ga7AuthorityReceipt(True, "admitted", token.operation)
        self._record(ledger, case, receipt)
        return receipt

    def _deny(
        self,
        ledger: Ga7Ledger | None,
        case: Ga7DiscoveryCaseInput,
        reason: str,
        operation: str,
    ) -> Ga7AuthorityReceipt:
        receipt = Ga7AuthorityReceipt(False, reason, operation)
        self._record(ledger, case, receipt)
        return receipt

    def _record(
        self,
        ledger: Ga7Ledger | None,
        case: Ga7DiscoveryCaseInput,
        receipt: Ga7AuthorityReceipt,
    ) -> None:
        if ledger is None:
            return
        ledger.append_receipt(
            receipt_id=f"auth:{case.case_key()}:{receipt.reason}",
            case_key=case.case_key(),
            receipt_type=Ga7ReceiptType.AUTHORITY,
            epistemic=Ga7EpistemicClass.DECLARED,
            payload={
                "admitted": receipt.admitted,
                "reason": receipt.reason,
                "operation": receipt.operation,
            },
        )
