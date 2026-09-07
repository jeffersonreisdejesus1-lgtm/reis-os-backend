"""Canonical receipt_hash for G0. No extra fields enter the hash.

Hash input = UTF-8 JSON object with exactly these keys, sorted,
separators (',', ':'), no whitespace. Values are the raw strings.

  model_id
  ocs_id
  receipt_id
  input_hash
  output_hash
  privacy_decision
  trace_id

receipt_hash = 'sha256:' + hexdigest
schema_version is NOT hashed (version is validated by schema const).
terminal_state / request_id are envelope metadata and NOT hashed.
"""
from __future__ import annotations

import hashlib
import json

HASH_KEYS = (
    "input_hash",
    "model_id",
    "ocs_id",
    "output_hash",
    "privacy_decision",
    "receipt_id",
    "trace_id",
)


def canonical_body(receipt: dict) -> str:
    body = {k: receipt[k] for k in HASH_KEYS}
    return json.dumps(body, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def receipt_hash(receipt: dict) -> str:
    return "sha256:" + hashlib.sha256(canonical_body(receipt).encode("utf-8")).hexdigest()


def verify(receipt: dict) -> bool:
    return receipt.get("receipt_hash") == receipt_hash(receipt)
