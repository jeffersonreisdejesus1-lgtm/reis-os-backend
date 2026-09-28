from __future__ import annotations

import json
import os
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence/ocsx/l1/gemini-assurance"
OUT.mkdir(parents=True, exist_ok=True)

MODEL = os.environ.get("OCSX_GEMINI_MODEL", "gemini-3.8-flash")
KEY = os.environ.get("GEMINI_API_KEY", "").strip()
if not KEY:
    raise SystemExit("GEMINI_API_KEY is missing")

source_paths = [
    "formal/ocsx/l1/OCSX-FOUNDER-POST-TRIAL-AUTHORIZATION-001.md",
    "formal/ocsx/l1/OCSX-L1-MATERIALIZATION-QUALIFICATION-ENVELOPE-001.md",
    "app/ocsx_l1/runtime.py",
    "tests/test_ocsx_l1_qualification.py",
    "evidence/ocsx/l1/OCSX-L1-QUALIFICATION-RESULT-001.json",
]

parts = []
for rel in source_paths:
    p = ROOT / rel
    parts.append(f"===== {rel} =====\n{p.read_text(encoding='utf-8')}\n")

prompt = """You are an independent audit-only assurance seat for REIS OS OCS-X L1 qualification.
Do not inherit the builder verdict. Audit only whether the L1 candidate is sufficiently qualified to advance to READY_FOR_FOUNDER_L1_DECISION.
PASS does not authorize production, canonical mutation, adoption, promotion, universal deployment, OURO access or merge.
Independently attack: founder authorization timing; L0 identity preservation; authority ceiling preservation; empty allowlist recovery; single writer; single stop; stop fencing; Progress/NoProgress/Fail semantics; UNKNOWN fail-closed; recovery determinism; forbidden effect isolation; builder evidence scope; overclaim.
Return ONLY valid JSON with exactly these top-level fields:
{
  \"object\": \"OCSX-L1-INDEPENDENT-QUALIFICATION-ASSURANCE-001\",
  \"provider\": \"GOOGLE_GEMINI_API\",
  \"model\": \"MODEL_USED\",
  \"target_evidence_head\": \"SOURCE_HEAD\",
  \"assurance_mode\": \"INDEPENDENT_AUDIT_ONLY\",
  \"founder_authorization\": \"PASS|FAIL|UNKNOWN\",
  \"l0_identity_preservation\": \"PASS|FAIL|UNKNOWN\",
  \"authority_ceiling_preservation\": \"PASS|FAIL|UNKNOWN\",
  \"empty_allowlist_recovery\": \"PASS|FAIL|UNKNOWN\",
  \"single_writer\": \"PASS|FAIL|UNKNOWN\",
  \"single_stop\": \"PASS|FAIL|UNKNOWN\",
  \"stop_fencing\": \"PASS|FAIL|UNKNOWN\",
  \"progress_semantics\": \"PASS|FAIL|UNKNOWN\",
  \"no_progress_t2_semantics\": \"PASS|FAIL|UNKNOWN\",
  \"fail_stop_semantics\": \"PASS|FAIL|UNKNOWN\",
  \"unknown_fail_closed\": \"PASS|FAIL|UNKNOWN\",
  \"recovery_determinism\": \"PASS|FAIL|UNKNOWN\",
  \"forbidden_effect_isolation\": \"PASS|FAIL|UNKNOWN\",
  \"builder_evidence_scope\": \"PASS|FAIL|UNKNOWN\",
  \"overclaim_check\": \"PASS|FAIL|UNKNOWN\",
  \"material_blockers\": [],
  \"reservations\": [],
  \"adversarial_findings\": [],
  \"verdict\": \"PASS|PASS_WITH_RESERVATIONS|HOLD|FAIL\",
  \"ready_for_founder_l1_decision\": false,
  \"production_authority\": false,
  \"canonical_mutation_authority\": false,
  \"adoption_authority\": false,
  \"promotion_authority\": false,
  \"universal_deployment_authority\": false,
  \"merge_authority\": false
}
ready_for_founder_l1_decision may be true only when no material blocker remains.
"""

source_head = os.environ.get("GITHUB_SHA", "UNKNOWN")
prompt = prompt.replace("SOURCE_HEAD", source_head).replace("MODEL_USED", MODEL)
prompt += "\n\n" + "\n".join(parts)

payload = {
    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
    "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
}
url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={KEY}"
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=120) as resp:
    raw = json.loads(resp.read().decode("utf-8"))

text = raw["candidates"][0]["content"]["parts"][0]["text"]
result = json.loads(text)

required_false = [
    "production_authority",
    "canonical_mutation_authority",
    "adoption_authority",
    "promotion_authority",
    "universal_deployment_authority",
    "merge_authority",
]
for key in required_false:
    if result.get(key) is not False:
        raise SystemExit(f"fail-closed: {key} must be false")

if result.get("verdict") not in {"PASS", "PASS_WITH_RESERVATIONS", "HOLD", "FAIL"}:
    raise SystemExit("fail-closed: invalid verdict")

(OUT / "assurance.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(OUT / "provider-response.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
