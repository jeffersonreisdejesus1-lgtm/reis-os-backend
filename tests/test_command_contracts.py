from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.command.domain.observation import (
    FreshnessState,
    ObservationContract,
    ObservationStatus,
)
from app.shared.database.base import Base
from app.shared.database.models import CommandSourceModel, ObservationModel


def make_observation(**overrides: object) -> ObservationContract:
    values: dict[str, object] = {
        "source_id": uuid4(),
        "source_object_type": "pull_request",
        "source_object_id": "1",
        "source_reference": "github://repo/pulls/1",
        "source_revision": "abc123",
        "observed_at": datetime.now(UTC),
        "retrieved_at": datetime.now(UTC),
        "payload_normalized": {"state": "open"},
        "observation_status": ObservationStatus.OBSERVED,
        "freshness_state": FreshnessState.FRESH,
        "current_confirmed": True,
    }
    values.update(overrides)
    return ObservationContract.model_validate(values)


def test_external_observation_requires_source_reference() -> None:
    with pytest.raises(ValidationError):
        make_observation(source_reference="")


@pytest.mark.parametrize(
    "freshness_state",
    [FreshnessState.STALE, FreshnessState.UNKNOWN, FreshnessState.CONFLICT],
)
def test_unreliable_freshness_cannot_be_current_confirmed(
    freshness_state: FreshnessState,
) -> None:
    with pytest.raises(ValidationError):
        make_observation(freshness_state=freshness_state)


@pytest.mark.parametrize(
    "status",
    [ObservationStatus.PARTIAL, ObservationStatus.ERROR],
)
def test_partial_or_error_cannot_be_fresh_current_confirmed(
    status: ObservationStatus,
) -> None:
    with pytest.raises(ValidationError):
        make_observation(
            observation_status=status,
            freshness_state=FreshnessState.FRESH,
            current_confirmed=True,
        )


def test_conflict_status_preserves_conflict_freshness() -> None:
    with pytest.raises(ValidationError):
        make_observation(
            observation_status=ObservationStatus.CONFLICT,
            freshness_state=FreshnessState.FRESH,
        )

    observation = make_observation(
        observation_status=ObservationStatus.CONFLICT,
        freshness_state=FreshnessState.CONFLICT,
        current_confirmed=False,
    )
    assert observation.freshness_state is FreshnessState.CONFLICT


def test_command_observation_tables_are_registered() -> None:
    assert CommandSourceModel.__tablename__ == "command_sources"
    assert ObservationModel.__tablename__ == "observations"
    assert "command_sources" in Base.metadata.tables
    assert "observations" in Base.metadata.tables
