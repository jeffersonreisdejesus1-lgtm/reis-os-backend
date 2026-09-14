from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256

from app.gica.ga7_ledger import Ga7Ledger


@dataclass(frozen=True)
class Ga7MetricSnapshot:
    case_key: str
    receipt_count: int
    dispositions: tuple[str, ...]
    completeness: bool
    snapshot_hash: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


class Ga7Metrics:
    def snapshot(self, ledger: Ga7Ledger, case_key: str) -> Ga7MetricSnapshot:
        rows = ledger.receipts(case_key)
        types = tuple(row["receipt_type"] for row in rows)
        complete = "AUTHORITY" in types and "GA7_DISCOVERY_CASE" in types
        payload = json.dumps({"types": types, "n": len(rows)}, sort_keys=True)
        digest = sha256(payload.encode()).hexdigest()
        return Ga7MetricSnapshot(case_key, len(rows), types, complete, digest)
