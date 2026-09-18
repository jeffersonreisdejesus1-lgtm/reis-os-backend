import pytest
from fastapi import HTTPException

from app.execution_bindings import ExecutionEnvelope, validate_envelope


PROGRAM_ID = "REIS-OS-ARTIFICIAL-BRAIN-VALIDATION-001"


def _envelope(**overrides):
    values = {
        "program_id": PROGRAM_ID,
        "gate": "AB6",
        "capability": "IMPLEMENT_PATCH",
        "founder_approval_ref": "founder://artificial-brain-program-001",
        "payload": {"change": "bounded"},
    }
    values.update(overrides)
    return ExecutionEnvelope(**values)


def test_authorized_program_scope_is_accepted(monkeypatch):
    monkeypatch.setenv(
        "REIS_ARTIFICIAL_BRAIN_FOUNDER_APPROVAL_REF",
        "founder://artificial-brain-program-001",
    )
    validate_envelope(_envelope())


@pytest.mark.parametrize("gate", ["AB5", "AB13", "DR9"])
def test_gate_outside_ab6_ab12_fails_closed(monkeypatch, gate):
    monkeypatch.setenv(
        "REIS_ARTIFICIAL_BRAIN_FOUNDER_APPROVAL_REF",
        "founder://artificial-brain-program-001",
    )
    with pytest.raises(HTTPException) as exc:
        validate_envelope(_envelope(gate=gate))
    assert exc.value.status_code == 403
    assert exc.value.detail == "GATE_OUTSIDE_AUTONOMOUS_SCOPE"


@pytest.mark.parametrize(
    "capability",
    ["GITHUB_MERGE_PR", "FOUNDER_PROMOTION", "AB13_PROMOTION"],
)
def test_founder_reserved_capabilities_are_denied(monkeypatch, capability):
    monkeypatch.setenv(
        "REIS_ARTIFICIAL_BRAIN_FOUNDER_APPROVAL_REF",
        "founder://artificial-brain-program-001",
    )
    with pytest.raises(HTTPException) as exc:
        validate_envelope(_envelope(capability=capability))
    assert exc.value.status_code == 403
    assert exc.value.detail == "FOUNDER_RESERVED_CAPABILITY"


def test_missing_founder_binding_fails_closed(monkeypatch):
    monkeypatch.delenv("REIS_ARTIFICIAL_BRAIN_FOUNDER_APPROVAL_REF", raising=False)
    with pytest.raises(HTTPException) as exc:
        validate_envelope(_envelope())
    assert exc.value.status_code == 503
    assert exc.value.detail == "FOUNDER_APPROVAL_BINDING_REQUIRED"


def test_founder_reference_mismatch_is_denied(monkeypatch):
    monkeypatch.setenv(
        "REIS_ARTIFICIAL_BRAIN_FOUNDER_APPROVAL_REF",
        "founder://artificial-brain-program-001",
    )
    with pytest.raises(HTTPException) as exc:
        validate_envelope(_envelope(founder_approval_ref="founder://other"))
    assert exc.value.status_code == 403
    assert exc.value.detail == "FOUNDER_APPROVAL_MISMATCH"
