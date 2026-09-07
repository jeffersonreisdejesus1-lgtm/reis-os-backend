from pathlib import Path

import pytest

from app.command.atlas_semantic import (
    CATALOG_SCOPE_ID,
    NORMALIZATION_VERSION,
    AntiThesisRule,
    AtlasSemanticError,
    Decision,
    EdgeType,
    Severity,
    aggregate_path_severities,
    load_yaml,
    match_antitheses,
    semantic_catalog_sha_from_yaml,
    validate_catalog,
)

FIXTURE = Path(
    "contracts/control-plane-physiology-atlas/a1/minimal-atlas-fixture.yaml"
)


def test_closed_vocabulary_is_exact_v0() -> None:
    assert {item.value for item in EdgeType} == {
        "COMPOSES",
        "REQUIRES",
        "GOVERNED_BY",
        "EVIDENCED_BY",
    }


def test_depends_on_is_rejected_as_hold_unknown_edge_type() -> None:
    catalog = load_yaml(FIXTURE.read_text(encoding="utf-8"))
    catalog["edges"][0]["type"] = "DEPENDS_ON"
    with pytest.raises(AtlasSemanticError, match="HOLD_UNKNOWN_EDGE_TYPE"):
        validate_catalog(catalog)


def test_catalog_scope_and_normalization_are_normative() -> None:
    catalog = load_yaml(FIXTURE.read_text(encoding="utf-8"))
    validate_catalog(catalog)
    assert catalog["catalog_scope_id"] == CATALOG_SCOPE_ID
    assert catalog["normalization_version"] == NORMALIZATION_VERSION


def test_deny_is_decision_not_severity() -> None:
    assert "DENY" not in {item.value for item in Severity}
    rule = AntiThesisRule(
        rule_id="deny-runtime",
        priority=1,
        field="claim_kind",
        equals="RUNTIME_CAUSAL_EVENT",
        decision=Decision.DENY,
    )
    result = match_antitheses(
        {"claim_kind": "RUNTIME_CAUSAL_EVENT"},
        Severity.INFORMATIONAL,
        [rule],
        Severity.HOLD,
    )
    assert result.decision is Decision.DENY
    assert result.severity is Severity.INFORMATIONAL


def test_match_order_and_caps_are_deterministic() -> None:
    rules = [
        AntiThesisRule(
            rule_id="z-cap",
            priority=5,
            field="kind",
            equals="claim",
            severity_cap=Severity.HOLD,
        ),
        AntiThesisRule(
            rule_id="a-cap",
            priority=5,
            field="kind",
            equals="claim",
            severity_cap=Severity.DEGRADE,
        ),
    ]
    result = match_antitheses(
        {"kind": "claim"}, Severity.FAIL, rules, Severity.HOLD
    )
    assert [match.rule_id for match in result.matches] == ["a-cap", "z-cap"]
    assert result.severity is Severity.DEGRADE


def test_never_upgrades_cross_path() -> None:
    result = aggregate_path_severities(
        [Severity.INFORMATIONAL, Severity.DEGRADE], Severity.HOLD
    )
    assert result is Severity.DEGRADE


def test_t25_structure_differs_from_causal_semantics() -> None:
    structural_graph = {
        "nodes": ["OCS:NOESIS", "COMP:ORCHESTRATION"],
        "edges": [("E1", "COMPOSES")],
    }
    rule = AntiThesisRule(
        rule_id="cap",
        priority=1,
        field="kind",
        equals="claim",
        severity_cap=Severity.HOLD,
    )
    result_a = match_antitheses(
        {"kind": "claim"}, Severity.FAIL, [rule], Severity.HOLD
    )
    result_b = match_antitheses(
        {"kind": "claim"}, Severity.FAIL, [rule], Severity.DEGRADE
    )
    assert structural_graph == structural_graph.copy()
    assert result_a.severity is Severity.HOLD
    assert result_b.severity is Severity.DEGRADE


def test_t26_yaml_serialization_does_not_change_semantic_sha() -> None:
    yaml_a = """
    catalog_scope_id: reis-os/control-plane/physiology-atlas/v0
    normalization_version: atlas-semantic-v1
    nodes: [A, B]
    edges: []
    thesis_packages: []
    rules: []
    bindings: []
    """
    yaml_b = """
    # same semantic catalog, different map order and formatting
    bindings: [ ]
    rules: []
    thesis_packages: []
    edges: []
    nodes:
      - A
      - B
    normalization_version: atlas-semantic-v1
    catalog_scope_id: "reis-os/control-plane/physiology-atlas/v0"
    """
    assert semantic_catalog_sha_from_yaml(yaml_a) == semantic_catalog_sha_from_yaml(
        yaml_b
    )


def test_duplicate_yaml_keys_are_rejected() -> None:
    with pytest.raises(AtlasSemanticError, match="duplicate mapping key"):
        load_yaml("a: 1\na: 2\n")
