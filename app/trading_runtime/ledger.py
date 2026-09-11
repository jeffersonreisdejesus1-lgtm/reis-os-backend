from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from threading import Lock
from uuid import uuid4


@dataclass(frozen=True)
class EvidenceEvent:
    event_id: str
    causal_parent_id: str | None
    run_id: str
    event_type: str
    input_hash: str
    output_hash: str
    config_hash: str
    data_snapshot_ref: str
    predecessor: str | None
    created_at: str


class EvidenceLedger:
    def __init__(self) -> None:
        self._events: list[EvidenceEvent] = []
        self._lock = Lock()

    @staticmethod
    def hash_payload(payload: object) -> str:
        encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()
        return sha256(encoded).hexdigest()

    def append(
        self,
        *,
        run_id: str,
        event_type: str,
        input_payload: object,
        output_payload: object,
        config_payload: object,
        data_snapshot_ref: str,
        causal_parent_id: str | None = None,
        predecessor: str | None = None,
    ) -> EvidenceEvent:
        event = EvidenceEvent(
            event_id=str(uuid4()),
            causal_parent_id=causal_parent_id,
            run_id=run_id,
            event_type=event_type,
            input_hash=self.hash_payload(input_payload),
            output_hash=self.hash_payload(output_payload),
            config_hash=self.hash_payload(config_payload),
            data_snapshot_ref=data_snapshot_ref,
            predecessor=predecessor,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._events.append(event)
        return event

    def events(self) -> list[dict[str, object]]:
        with self._lock:
            return [asdict(event) for event in self._events]
