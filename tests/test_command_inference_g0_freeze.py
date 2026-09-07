from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType

BASE = Path(__file__).resolve().parents[1] / "contracts" / "command-inference-g0"

PINNED = {
    "g0-inference-request.schema.json": (
        727,
        "1901fbc186ceff97b307ffc8fd22b1ae4481dff386af34ae48cfd377a493998c",
    ),
    "g0-inference-receipt.schema.json": (
        1079,
        "872cdb27cc0493f7cb69a9a607304643a9820fa6c97b1f6f88b385c566831bf6",
    ),
    "g0-canonical-payload.json": (
        517,
        "590801c10b60c7bb829fc782e14cf7d94330fcf85856d5f4c4329fa5292686cf",
    ),
    "receipt_hash.py": (
        1081,
        "3321079f1591a0cb8dd9051885af55cdb93b85963b43aab8425b7eadf081e099",
    ),
}

REQUIRED_RECEIPT_FIELDS = {
    "schema_version",
    "receipt_id",
    "input_hash",
    "output_hash",
    "privacy_decision",
    "model_id",
    "ocs_id",
    "trace_id",
    "receipt_hash",
}

PRIVACY_DECISIONS = {
    "ALLOW_LOCAL",
    "ALLOW_REMOTE",
    "DENY_REMOTE",
    "DENY_ALL",
}

PROHIBITED_CONTENT_FIELDS = {
    "prompt",
    "completion",
    "groundedness",
    "groundedness_score",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(name: str) -> dict[str, object]:
    return json.loads((BASE / name).read_text(encoding="utf-8"))


def _load_hash_module() -> ModuleType:
    path = BASE / "receipt_hash.py"
    spec = importlib.util.spec_from_file_location("g0_receipt_hash", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_contract_bytes_match_institutional_pins() -> None:
    for name, (expected_size, expected_sha256) in PINNED.items():
        path = BASE / name
        assert path.stat().st_size == expected_size
        assert _sha256(path) == expected_sha256


def test_sha256sums_pins_the_four_contract_artifacts() -> None:
    declared: dict[str, str] = {}
    for line in (BASE / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        declared[name] = digest

    for name, (_, expected_sha256) in PINNED.items():
        assert declared[name] == expected_sha256


def test_receipt_schema_keeps_g0_center_closed() -> None:
    schema = _load_json("g0-inference-receipt.schema.json")
    properties = schema["properties"]
    assert isinstance(properties, dict)

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == REQUIRED_RECEIPT_FIELDS
    assert set(properties["privacy_decision"]["enum"]) == PRIVACY_DECISIONS
    assert PROHIBITED_CONTENT_FIELDS.isdisjoint(properties)


def test_request_schema_is_fail_closed_and_contains_no_content_fields() -> None:
    schema = _load_json("g0-inference-request.schema.json")
    properties = schema["properties"]
    assert isinstance(properties, dict)

    assert schema["additionalProperties"] is False
    assert PROHIBITED_CONTENT_FIELDS.isdisjoint(properties)


def test_canonical_example_has_no_content_and_hash_verifies() -> None:
    payload = _load_json("g0-canonical-payload.json")
    assert PROHIBITED_CONTENT_FIELDS.isdisjoint(payload)

    module = _load_hash_module()
    assert module.receipt_hash(payload) == payload["receipt_hash"]
    assert module.verify(payload) is True
    assert payload["receipt_hash"] == (
        "sha256:c0d29b772dabd9bb7e76d643674813eafe0f6e22d11221a677e1aa49d739c515"
    )


def test_receipt_hash_commits_only_the_frozen_seven_semantic_fields() -> None:
    module = _load_hash_module()
    assert set(module.HASH_KEYS) == {
        "receipt_id",
        "input_hash",
        "output_hash",
        "privacy_decision",
        "model_id",
        "ocs_id",
        "trace_id",
    }
