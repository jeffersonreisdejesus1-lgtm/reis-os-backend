from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

BASE_SHA = "691d738823b52265af6a268a287e3475e446a4b7f3aaec681856b3f27cdcd06c"
PATCH_SHA = "5a73d8b59783d654683f88a5931ca0a6bc6618ed6ad5946ff0d785a56c6c7f95"
EXPECTED_REPORT_SHA = "c2e4a5f891fbdcbd1e4d141b3dc80638f285564a77a13944c5b62a041bfc5b87"
ROOT_NAME = "NOESIS_NATIVE_EC007_20260823_v0.2.1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_pytest(root: Path) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", str(root)], text=True, capture_output=True)
    if proc.returncode:
        raise SystemExit(proc.stdout + proc.stderr)
    return proc.returncode, proc.stdout.strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("base_zip", type=Path)
    ap.add_argument("sealed_patch", type=Path)
    args = ap.parse_args()

    if sha(args.base_zip) != BASE_SHA:
        raise SystemExit("BASE_SHA_MISMATCH")
    if sha(args.sealed_patch) != PATCH_SHA:
        raise SystemExit("PATCH_SHA_MISMATCH")

    with tempfile.TemporaryDirectory(prefix="noesis-independent-replay-") as td:
        work = Path(td)
        base_clean = work / "base_clean"
        base_clean.mkdir()
        with zipfile.ZipFile(args.base_zip) as zf:
            zf.extractall(base_clean)
        base = base_clean / ROOT_NAME
        candidate = work / ROOT_NAME
        shutil.copytree(base, candidate)

        patch = subprocess.run(["patch", "-p0", "-i", str(args.sealed_patch)], cwd=work, text=True, capture_output=True)
        if patch.returncode:
            raise SystemExit(patch.stdout + patch.stderr)

        _, baseline = run_pytest(base)
        _, candidate_tests = run_pytest(candidate)
        qual = subprocess.run([sys.executable, "tools/run_layered_refactor_qualification.py"], cwd=candidate, text=True, capture_output=True)
        if qual.returncode:
            raise SystemExit(qual.stdout + qual.stderr)

        report = json.loads((candidate / "artifacts/NOESIS_LAYERED_REFACTOR_QUALIFICATION_001.json").read_text())
        result = {
            "base_sha256": sha(args.base_zip),
            "patch_sha256": sha(args.sealed_patch),
            "baseline_pytest": baseline.splitlines()[-1],
            "candidate_pytest": candidate_tests.splitlines()[-1],
            "native_cognition_equivalence": report["native_cognition_equivalence"],
            "all_l0_preserved": all(s["l0_preserved"] for s in report["stages"]),
            "forbidden_probe_status": report["forbidden_transition_probe"]["status"],
            "qualification_report_sha256": report["report_sha256"],
            "qualification_report_sha_match": report["report_sha256"] == EXPECTED_REPORT_SHA,
        }
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
