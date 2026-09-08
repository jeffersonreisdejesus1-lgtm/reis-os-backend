from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "ocsx-gemini-pretrial-assurance"
OUT.mkdir(parents=True, exist_ok=True)
KEY = (os.getenv("GEMINI_API_KEY") or "").strip()
MODEL = os.getenv("OCSX_GEMINI_MODEL", "gemini-3.7-flash")
SOURCE_HEAD = os.getenv("GITHUB_SHA", "UNKNOWN")

FILES = [
    "formal/ocsx/preparation/OCSX-PRETRIAL-READINESS-READBACK-001.md",
    "formal/ocsx/preparation/OCSX-EXPERIMENT-PREPARATION-ENVELOPE-001.md",
    "formal/ocsx/preparation/OCSX-AUTHORITY-ISOLATION-ENVELOPE-001.md",
    "formal/ocsx/preparation/OCSX-EVIDENCE-AND-READBACK-CONTRACT-001.md",
    "formal/ocsx/preparation/OCSX-TRIAL-DESIGN-PREREGISTRATION-001.md",
    "formal/ocsx/preparation/OCSX-OUTCOME-CLASSIFICATION-CONTRACT-001.md",
    "formal/ocsx/preparation/OCSX-REPRODUCIBILITY-MANIFEST-001.md",
    "formal/ocsx/preparation/OCSX-PAIRED-TASKSET-001.json",
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_payload() -> tuple[str, dict[str, str]]:
    hashes: dict[str, str] = {}
    sections: list[str] = []
    for rel in FILES:
        raw = (ROOT / rel).read_bytes()
        hashes[rel] = sha256(raw)
        text = raw.decode("utf-8")
        sections.append(f"\n===== {rel} =====\n{text[:12000]}")
    prompt = f"""You are an independent adversarial assurance reviewer for REIS OS OCS-X pretrial preparation.

Exact source HEAD: {SOURCE_HEAD}

Judge ONLY whether the package is materially ready to advance from PRETRIAL PREPARATION to READY_FOR_TRIAL_AUTHORIZATION_REVIEW. This is not authorization to create OCS-X or execute a trial.

Required constitutional boundaries:
- CAPABILITY != AUTHORITY
- EXECUTION != EVIDENCE
- EVIDENCE != ASSURANCE
- ASSURANCE != PROMOTION
- UNKNOWN != ZERO
- OCS_X_CREATION remains forbidden
- L1_ACTIVATION remains forbidden
- TRIAL_EXECUTION remains forbidden
- PRODUCTION_ROUTING remains forbidden
- CANONICAL_STATE_WRITE remains forbidden
- ADOPTION remains forbidden

Falsify especially: taskset freeze, reference freeze, M01-M13 fail-closed evidence semantics, authority/namespace isolation, single writer/stop, recovery identity stability, Progress/NoProgress/Fail semantics, reproducibility bindings, and overclaim.

Return ONLY JSON with exactly these fields:
{{
  "assurance_classification": "INDEPENDENT_GEMINI_PRETRIAL_ASSURANCE",
  "source_head": "{SOURCE_HEAD}",
  "material_blockers": ["..."],
  "reservations": ["..."],
  "verdict": "PASS|PASS_WITH_RESERVATIONS|HOLD|FAIL",
  "ready_for_trial_authorization_review": true,
  "trial_authority_granted": false,
  "ocs_x_created": false,
  "trial_executed": false
}}

Artifacts follow:
{''.join(sections)}
"""
    return prompt, hashes


def main() -> None:
    prompt, hashes = build_payload()
    if not KEY:
        result = {
            "status": "HOLD_CREDENTIAL_OR_ACCESS_BLOCKER",
            "source_head": SOURCE_HEAD,
            "model": MODEL,
            "artifact_hashes": hashes,
        }
        (OUT / "assurance.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        raise SystemExit(2)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={KEY}"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 1800, "responseMimeType": "application/json"},
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            response_body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error = exc.read().decode("utf-8")[:1000]
        (OUT / "provider-error.txt").write_text(f"HTTP_{exc.code}\n{error}\n", encoding="utf-8")
        raise

    text = "".join(
        part.get("text", "")
        for candidate in response_body.get("candidates", [])
        for part in candidate.get("content", {}).get("parts", [])
    ).strip()
    parsed = json.loads(text)
    parsed["execution_provider"] = "gemini"
    parsed["execution_model"] = MODEL
    parsed["source_head"] = SOURCE_HEAD
    parsed["artifact_hashes"] = hashes
    parsed["usage_metadata"] = response_body.get("usageMetadata", {})
    (OUT / "assurance.json").write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(parsed, indent=2, ensure_ascii=False))

    if parsed.get("verdict") not in {"PASS", "PASS_WITH_RESERVATIONS"}:
        raise SystemExit(3)
    if parsed.get("ready_for_trial_authorization_review") is not True:
        raise SystemExit(4)
    if parsed.get("trial_authority_granted") is not False:
        raise SystemExit(5)
    if parsed.get("ocs_x_created") is not False or parsed.get("trial_executed") is not False:
        raise SystemExit(6)


if __name__ == "__main__":
    main()
