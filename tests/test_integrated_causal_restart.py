from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROBE = r'''
import json, os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from app.materialization.coi import CognitiveOperationalIntegration
root = Path(sys.argv[2])
coi = CognitiveOperationalIntegration()
receipt = coi.realize(
    actor="SOFIA",
    identity="ocs://sofia",
    intent="hello-integrated",
    mission_id="M-INT",
    bound_object="object://integrated",
    workdir=root,
)
print(json.dumps({
    "pid": os.getpid(),
    "disposition": receipt.disposition.value,
    "material": receipt.material,
    "promoted": receipt.promoted,
    "failure": receipt.failure,
    "recursive_replayed": receipt.recursive_replayed,
    "recursive_reason": receipt.recursive_reason,
    "bound_object": receipt.bound_object,
}))
'''


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "app" / "materialization" / "coi.py").exists():
            return parent
    return Path.cwd()


def _run(repo: Path, work: Path) -> dict:
    completed = subprocess.run(
        [sys.executable, "-c", PROBE, str(repo), str(work)],
        capture_output=True, text=True, check=False, cwd=str(repo),
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    return json.loads(completed.stdout.strip().splitlines()[-1])


def test_integrated_two_process_coi_factory_no_promotion(tmp_path: Path) -> None:
    repo = _repo_root()
    p1 = _run(repo, tmp_path)
    p2 = _run(repo, tmp_path)
    assert p1["pid"] != p2["pid"]
    assert p1["material"] is True
    assert p1["promoted"] is False
    assert p1["recursive_replayed"] is False
    assert p2["material"] is True
    assert p2["promoted"] is False
    assert p2["recursive_replayed"] is True
    assert p2["recursive_reason"] == "replay_blocked"
    artifacts = list((tmp_path / "factory-fx").glob("*.txt"))
    assert len(artifacts) == 1
    assert artifacts[0].name == "object_integrated.txt"
    assert artifacts[0].read_text(encoding="utf-8") == "hello-integrated"
