# G0 material schema verification

```
G0_ARCHITECTURAL_FREEZE              = TRUE
G0_CONTRACT_DEFINITION               = FROZEN
THREE_JSON_SCHEMA_FILES_DECLARED     = TRUE
THREE_JSON_SCHEMA_FILES_OBSERVED     = TRUE
G0_MATERIAL_SCHEMA_VERIFICATION      = PASS
ARCHITECTURAL_REOPEN                 = FALSE
```

Observed on this host, path `/home/workdir/artifacts/reis-os-inference/schema/`:

| File | SHA-256 |
|---|---|
| g0-inference-request.schema.json | `1901fbc186ceff97b307ffc8fd22b1ae4481dff386af34ae48cfd377a493998c` |
| g0-inference-receipt.schema.json | `872cdb27cc0493f7cb69a9a607304643a9820fa6c97b1f6f88b385c566831bf6` |
| g0-canonical-payload.json | `590801c10b60c7bb829fc782e14cf7d94330fcf85856d5f4c4329fa5292686cf` |
| receipt_hash.py | `3321079f1591a0cb8dd9051885af55cdb93b85963b43aab8425b7eadf081e099` |

Checks:

- JSON parse = PASS
- `additionalProperties: false` on both schemas = PASS
- receipt required includes four center fields + `model_id` + `ocs_id` + `trace_id` + `receipt_hash` + `schema_version` = PASS
- no prompt / completion / groundedness properties = PASS
- `terminal_state` optional (journal envelope) = PASS
- canonical hash verified against payload = PASS

`receipt_hash` body (sorted keys, compact JSON):
`input_hash`, `model_id`, `ocs_id`, `output_hash`, `privacy_decision`, `receipt_id`, `trace_id`

Correction made during verification (center only):
`model_id`, `ocs_id`, `trace_id` moved from optional to required so the hash function is total.
Placeholder `cccc…` in the sample payload replaced by the computed digest
`sha256:c0d29b772dabd9bb7e76d643674813eafe0f6e22d11221a677e1aa49d739c515`.
