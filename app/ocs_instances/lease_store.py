from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

from app.universal_kernel.governance import (
    AuthenticatedLeaseSnapshot,
    AuthorityLease,
    AuthorityLeaseManager,
    LeaseSnapshot,
    LeaseState,
)


class AuthenticatedLeaseSnapshotStore:
    """Atomic, authenticated persistence adapter for authority lease state."""

    def __init__(self, path: str | Path, authentication_key: bytes) -> None:
        if not authentication_key:
            raise ValueError("lease_snapshot_authentication_key_required")
        self._path = Path(path)
        self._key = authentication_key

    def save(self, manager: AuthorityLeaseManager) -> None:
        signed = manager.authenticated_snapshot(self._key)
        payload = {
            "algorithm": signed.algorithm,
            "mac": signed.mac,
            "snapshots": [asdict(item) for item in signed.snapshots],
        }
        temporary = self._path.with_suffix(f"{self._path.suffix}.tmp")
        temporary.write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        os.replace(temporary, self._path)

    def load(self) -> AuthorityLeaseManager:
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        snapshots = tuple(
            LeaseSnapshot(
                lease=AuthorityLease(
                    **{
                        **item["lease"],
                        "scope": tuple(item["lease"]["scope"]),
                        "state": LeaseState(item["lease"]["state"]),
                    }
                ),
                reservations=tuple(
                    tuple(value) for value in item["reservations"]
                ),
            )
            for item in payload["snapshots"]
        )
        signed = AuthenticatedLeaseSnapshot(
            snapshots=snapshots,
            mac=str(payload["mac"]),
            algorithm=str(payload["algorithm"]),
        )
        return AuthorityLeaseManager.from_snapshot(
            signed, authentication_key=self._key
        )
