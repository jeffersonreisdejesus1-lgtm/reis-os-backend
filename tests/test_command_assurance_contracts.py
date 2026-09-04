from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.command.domain.assurance import (
    AssuranceResult,
    AssuranceStatus,
    AssuranceVerdict,
    HomologationState,
)


def valid_completed(**overrides: object) -> AssuranceResult:
    values: dict[str, object] = {
        "assurance_id": uuid4(),
        "object_key": "github:repo:pull_request:1",
        "scope": "command-slice",
        "status": AssuranceStatus.COMPLETED,
        "material": True,
        "verdict": AssuranceVerdict.PASS,
        "evidence_refs": ("ci://run/1",),
        "performer_ref": "synesis",
        "completed_at": datetime.now(UTC),
        "source_reference": "notion://assurance/1",
        "source_revision": "rev-1",
        "homologation_state": HomologationState.NOT_HOMOLOGATED,
    }
    values.update(overrides)
    return AssuranceResult.model_validate(values)


def test_completed_material_requires_verdict() -> None:
    with pytest.raises(ValidationError):
        valid_completed(verdict=None)


def test_completed_material_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        valid_completed(evidence_refs=())


def test_pending_cannot_carry_final_verdict() -> None:
    with pytest.raises(ValidationError):
        AssuranceResult(
            object_key="github:repo:pull_request:1",
            scope="command-slice",
            status=AssuranceStatus.PENDING,
            material=True,
            verdict=AssuranceVerdict.PASS,
            performer_ref="synesis",
        )


def test_pass_does_not_create_homologation() -> None:
    result = valid_completed(verdict=AssuranceVerdict.PASS)
    assert result.verdict is AssuranceVerdict.PASS
    assert result.homologation_state is HomologationState.NOT_HOMOLOGATED


@pytest.mark.parametrize(
    "verdict",
    [
        AssuranceVerdict.PASS,
        AssuranceVerdict.HOLD,
        AssuranceVerdict.FAIL,
        AssuranceVerdict.INDETERMINATE,
    ],
)
def test_material_verdicts_remain_explicit(verdict: AssuranceVerdict) -> None:
    result = valid_completed(verdict=verdict)
    assert result.verdict is verdict
