from __future__ import annotations

from dataclasses import dataclass

from .increment_receipt import IncrementReceipt


class IncrementReceiptConflict(ValueError):
    pass


@dataclass
class InMemoryIncrementLedger:
    _records: dict[str, str]

    def __init__(self) -> None:
        self._records = {}

    def put(self, receipt: IncrementReceipt) -> str:
        canonical = receipt.canonical_json()
        previous = self._records.get(receipt.receipt_id)
        if previous is not None and previous != canonical:
            raise IncrementReceiptConflict("conflicting_receipt_payload")
        self._records[receipt.receipt_id] = canonical
        return receipt.receipt_id

    def get(self, receipt_id: str) -> str | None:
        return self._records.get(receipt_id)
