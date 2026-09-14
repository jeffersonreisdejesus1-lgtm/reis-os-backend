from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKSET = ROOT / "formal/ocsx/preparation/OCSX-PAIRED-TASKSET-001.json"
EXPECTED_TASKS_HASH = "ec203ca89e266d0968561cc83ebae0a2a4d9c7075407d0d4a992081574e12415"
EXPECTED_REFERENCE = "NOESIS/EC-NOESIS-007"
EXPECTED_IDS = {f"PT-{index:03d}" for index in range(1, 9)}


def canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    data = json.loads(TASKSET.read_text(encoding="utf-8"))
    assert data["status"] == "FROZEN_BEFORE_TRIAL_AUTHORIZATION"
    assert data["reference"] == EXPECTED_REFERENCE
    assert data["selection_policy"].startswith("ALL_TASKS_RUN_ON_BOTH_SIDES")
    tasks = data["tasks"]
    assert set(tasks) == EXPECTED_IDS

    canonical_tasks: dict[str, dict[str, object]] = {}
    for task_id in sorted(tasks):
        task = tasks[task_id]
        payload_material = {
            "class": task["class"],
            "payload": task["payload"],
            "tools": task["tools"],
            "external_data": task["external_data"],
        }
        assert canonical_sha256(payload_material) == task["payload_sha256"]
        assert task["tools"] == []
        assert task["external_data"] == "DENY"
        assert task["required_evidence"]
        canonical_tasks[task_id] = payload_material

    actual_tasks_hash = canonical_sha256(canonical_tasks)
    assert actual_tasks_hash == EXPECTED_TASKS_HASH
    assert data["taskset_sha256"] == EXPECTED_TASKS_HASH

    print("OCSX_PRETRIAL_PACKAGE_VALIDATION=PASS")
    print(f"TASK_COUNT={len(tasks)}")
    print(f"TASKSET_SHA256={actual_tasks_hash}")
    print(f"REFERENCE={EXPECTED_REFERENCE}")
    print("TOOLS=EMPTY_ALLOWLIST")
    print("EXTERNAL_DATA=DENY")


if __name__ == "__main__":
    main()
