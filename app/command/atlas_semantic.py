from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
import hashlib
import math
from typing import Any, Mapping, Sequence
import unicodedata

import yaml

CATALOG_SCOPE_ID = "reis-os/control-plane/physiology-atlas/v0"
NORMALIZATION_VERSION = "atlas-semantic-v1"


class EdgeType(str, Enum):
    COMPOSES = "COMPOSES"
    REQUIRES = "REQUIRES"
    GOVERNED_BY = "GOVERNED_BY"
    EVIDENCED_BY = "EVIDENCED_BY"


class Severity(str, Enum):
    FAIL = "FAIL"
    HOLD = "HOLD"
    DEGRADE = "DEGRADE"
    INFORMATIONAL = "INFORMATIONAL"
    NONE = "NONE"


SEVERITY_RANK: dict[Severity, int] = {
    Severity.NONE: 0,
    Severity.INFORMATIONAL: 1,
    Severity.DEGRADE: 2,
    Severity.HOLD: 3,
    Severity.FAIL: 4,
}


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class AtlasSemanticError(ValueError):
    pass


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(
    loader: _UniqueKeyLoader, node: yaml.nodes.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise AtlasSemanticError(f"duplicate mapping key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def load_yaml(source: str) -> Any:
    return yaml.load(source, Loader=_UniqueKeyLoader)


def _canonical_number(value: int | float | Decimal) -> str:
    if isinstance(value, bool):
        raise AtlasSemanticError("boolean is not a canonical number")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise AtlasSemanticError("non-finite numbers are prohibited")
        value = Decimal(str(value))
    elif isinstance(value, int):
        return str(value)
    try:
        decimal = value.normalize()
    except InvalidOperation as exc:
        raise AtlasSemanticError("invalid decimal") from exc
    if decimal == 0:
        return "0"
    text = format(decimal, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _encode(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float, Decimal)):
        return _canonical_number(value)
    if isinstance(value, str):
        normalized = unicodedata.normalize("NFC", value)
        import json

        return json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, Mapping):
        pairs: list[tuple[str, Any]] = []
        for key, child in value.items():
            if not isinstance(key, str):
                raise AtlasSemanticError("catalog map keys must be strings")
            pairs.append((unicodedata.normalize("NFC", key), child))
        pairs.sort(key=lambda item: item[0].encode("utf-8"))
        return "{" + ",".join(f"{_encode(key)}:{_encode(child)}" for key, child in pairs) + "}"
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return "[" + ",".join(_encode(item) for item in value) + "]"
    raise AtlasSemanticError(f"unsupported catalog value: {type(value).__name__}")


def canonical_semantic_bytes(catalog: Any) -> bytes:
    return _encode(catalog).encode("utf-8")


def semantic_catalog_sha(catalog: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_semantic_bytes(catalog)).hexdigest()


def semantic_catalog_sha_from_yaml(source: str) -> str:
    return semantic_catalog_sha(load_yaml(source))


def validate_catalog(catalog: Mapping[str, Any]) -> None:
    allowed_top = {
        "catalog_scope_id",
        "normalization_version",
        "nodes",
        "edges",
        "thesis_packages",
        "rules",
        "bindings",
    }
    unknown = set(catalog) - allowed_top
    if unknown:
        raise AtlasSemanticError(f"unknown catalog fields: {sorted(unknown)}")
    if catalog.get("catalog_scope_id") != CATALOG_SCOPE_ID:
        raise AtlasSemanticError("invalid catalog_scope_id")
    if catalog.get("normalization_version") != NORMALIZATION_VERSION:
        raise AtlasSemanticError("invalid normalization_version")
    for edge in catalog.get("edges", []):
        edge_type = edge.get("type")
        try:
            EdgeType(edge_type)
        except ValueError as exc:
            raise AtlasSemanticError(
                f"HOLD_UNKNOWN_EDGE_TYPE: {edge_type!r}"
            ) from exc


@dataclass(frozen=True)
class AntiThesisRule:
    rule_id: str
    priority: int
    field: str
    equals: Any
    decision: Decision = Decision.ALLOW
    severity_cap: Severity | None = None


@dataclass(frozen=True)
class RuleMatch:
    rule_id: str
    priority: int
    decision: Decision
    severity_cap: Severity | None


@dataclass(frozen=True)
class MatchResult:
    decision: Decision
    severity: Severity
    matches: tuple[RuleMatch, ...]


def _cap_severity(value: Severity, cap: Severity | None) -> Severity:
    if cap is None:
        return value
    return value if SEVERITY_RANK[value] <= SEVERITY_RANK[cap] else cap


def aggregate_path_severities(
    paths: Sequence[Severity], thesis_cap: Severity
) -> Severity:
    if not paths:
        return Severity.NONE
    strongest = max(paths, key=SEVERITY_RANK.__getitem__)
    return _cap_severity(strongest, thesis_cap)


def match_antitheses(
    query_plan: Mapping[str, Any],
    proposed_severity: Severity,
    rules: Sequence[AntiThesisRule],
    thesis_cap: Severity,
) -> MatchResult:
    matches = [
        RuleMatch(rule.rule_id, rule.priority, rule.decision, rule.severity_cap)
        for rule in rules
        if query_plan.get(rule.field) == rule.equals
    ]
    matches.sort(key=lambda match: (match.priority, match.rule_id))
    if any(match.decision is Decision.DENY for match in matches):
        return MatchResult(Decision.DENY, proposed_severity, tuple(matches))
    severity = proposed_severity
    for match in matches:
        severity = _cap_severity(severity, match.severity_cap)
    severity = _cap_severity(severity, thesis_cap)
    return MatchResult(Decision.ALLOW, severity, tuple(matches))
