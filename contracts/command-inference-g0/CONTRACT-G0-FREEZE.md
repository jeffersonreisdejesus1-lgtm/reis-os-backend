# REIS OS — Inference contract freeze

STATUS = FROZEN_FOR_G0
PLANE  = Command / Cognition overlay
NOT    = runtime rebuild, B10 reopen, 11th OCS, device XNLI

Further work on NLI models, OTel regexes, batch tuners, or hallucination rubrics
does not change authority, state, or promotion. Stop expanding those surfaces.

## Four frozen fields

Every inference that may become institutional evidence carries exactly these
four central fields. Everything else is optional metadata.

| Field | Type | Meaning | Forbidden |
|---|---|---|---|
| `receipt_id` | ULID / UUID | Identity of this inference effect | Reuse across retries |
| `input_hash` | SHA-256 | Hash of request payload after redaction | Raw prompt in the field |
| `output_hash` | SHA-256 | Hash of model output / tool-intent blob | Raw completion in the field |
| `privacy_decision` | enum | `ALLOW_LOCAL` \| `ALLOW_REMOTE` \| `DENY_REMOTE` \| `DENY_ALL` | Implicit allow |

Integrity companion (not a fifth semantic field): `receipt_hash` over the
canonical JSON of the four fields + `model_id` + `ocs_id` + `trace_id`.

## Frozen decisions

1. MODEL ≠ OCS ≠ AUTHORITY
2. INFERENCE ≠ EXECUTION
3. RAG_HIT ≠ CANONICAL_EVIDENCE
4. UNRECEIPTED_INFERENCE ≠ EVIDENCE
5. Content capture default = OFF (`NO_CONTENT`)
6. Groundedness / XNLI / faithfulness = eval-worker only, promotion pack only
7. OTel production = metadata + allowlist; collector drops GenAI bodies
8. Device AI may SUGGEST; BIND stays on Binder / Execution Plane
9. XNLI alerts and batch size live on the eval plane, never Command SLOs

## Out of this freeze

- LiteRT-LM Engine init (AI-G1)
- Cloud GPU seat (AI-G4)
- Provider router (AI-G3)
- Legal trademark / CUPUWA naming
- Code authorization for product APK

## Next valid action

Nóesis writes G0 schemas only:

- `InferenceRequest` 1.0.0
- `InferenceReceipt` 1.0.0 with the four fields required
- `ApprovedModelManifest` stub (id, hash, approval_state)
- Policy order: privacy → route → authority

No new eval metric. No new collector regex. No new NLI checkpoint.
