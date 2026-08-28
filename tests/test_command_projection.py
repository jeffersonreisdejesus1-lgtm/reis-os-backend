from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.command.domain.observation import (
    FreshnessState,
    ObservationContract,
    ObservationStatus,
)
from app.command.domain.projection import (
    OperationalObjectContract,
    ProjectionBuilder,
)
from app.shared.database.base import Base
from app.shared.database.models import (
    OperationalObjectModel,
    ProjectionModel,
    ProjectionObservationModel,
)


def make_observation(
    freshness_state: FreshnessState = FreshnessState.FRESH,
) -> ObservationContract:
    status = ObservationStatus.OBSERVED
    if freshness_state is FreshnessState.CONFLICT:
        status = ObservationStatus.CONFLICT

    return ObservationContract(
        source_id=uuid4(),
        source_object_type="pull_request",
        source_object_id="1",
        source_reference="github://repo/pulls/1",
        observed_at=datetime.now(UTC),
        retrieved_at=datetime.now(UTC),
        payload_normalized={"state": "open"},
        observation_status=status,
        freshness_state=freshness_state,
        current_confirmed=freshness_state is FreshnessState.FRESH,
    )


def make_object() -> OperationalObjectContract:
    return OperationalObjectContract(
        object_key="github:repo:pull_request:1",
        object_type="pull_request",
        source_bindings=("github://repo/pulls/1",),
    )


def test_projection_requires_observation() -> None:
    builder = ProjectionBuilder()

    with pytest.raises(ValueError):
        builder.build(make_object(), "status", [], {"state": "open"})


def test_projection_preserves_observation_refs_and_worst_freshness() -> None:
    builder = ProjectionBuilder()
    fresh = make_observation(FreshnessState.FRESH)
    stale = make_observation(FreshnessState.STALE)

    projection = builder.build(
        make_object(),
        "status",
        [fresh, stale],
        {"state": "open"},
    )

    assert projection.observation_refs == (
        fresh.observation_id,
        stale.observation_id,
    )
    assert projection.freshness_state is FreshnessState.STALE


def test_conflict_remains_explicit_in_projection() -> None:
    builder = ProjectionBuilder()
    projection = builder.build(
        make_object(),
        "status",
        [make_observation(FreshnessState.CONFLICT)],
        {"state": "conflict"},
    )

    assert projection.freshness_state is FreshnessState.CONFLICT


def test_projection_rebuild_preserves_semantic_identity() -> None:
    builder = ProjectionBuilder()
    operational_object = make_object()
    observation = make_observation()

    first = builder.build(
        operational_object,
        "status",
        [observation],
        {"state": "open"},
    )
    rebuilt = builder.build(
        operational_object,
        "status",
        [observation],
        {"state": "open"},
    )

    assert first.object_key == rebuilt.object_key
    assert first.object_type == rebuilt.object_type
    assert first.observation_refs == rebuilt.observation_refs
    assert first.projection_payload == rebuilt.projection_payload
    assert first.freshness_state == rebuilt.freshness_state


def test_projection_tables_are_registered() -> None:
    assert OperationalObjectModel.__tablename__ == "operational_objects"
    assert ProjectionModel.__tablename__ == "projections"
    assert ProjectionObservationModel.__tablename__ == "projection_observations"
    assert "operational_objects" in Base.metadata.tables
    assert "projections" in Base.metadata.tables
    assert "projection_observations" in Base.metadata.tables
