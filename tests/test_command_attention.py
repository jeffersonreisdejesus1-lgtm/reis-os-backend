from datetime import UTC, datetime
from uuid import uuid4

from app.command.domain.attention import (
    AttentionClass,
    AttentionEngine,
    AttentionSeverity,
)
from app.command.domain.observation import FreshnessState
from app.command.domain.projection import ProjectionContract
from app.shared.database.base import Base
from app.shared.database.models import (
    AttentionItemModel,
    AttentionProjectionRefModel,
)


def make_projection(
    *,
    freshness_state: FreshnessState = FreshnessState.FRESH,
    payload: dict[str, object] | None = None,
) -> ProjectionContract:
    return ProjectionContract(
        object_key="github:repo:pull_request:1",
        object_type="pull_request",
        projection_type="status",
        observation_refs=(uuid4(),),
        built_at=datetime.now(UTC),
        projection_version=1,
        freshness_state=freshness_state,
        projection_payload=payload or {},
    )


def test_attention_engine_marks_conflict_as_p1() -> None:
    items = AttentionEngine().evaluate(
        make_projection(freshness_state=FreshnessState.CONFLICT)
    )

    assert len(items) == 1
    assert items[0].attention_class is AttentionClass.CONFLICT
    assert items[0].severity is AttentionSeverity.P1
    assert items[0].projection_refs
    assert items[0].evidence_refs
    assert items[0].derived_projection is True


def test_attention_engine_is_deterministic_and_explainable() -> None:
    projection = make_projection(
        payload={
            "blocked": True,
            "authority_missing": True,
        }
    )
    engine = AttentionEngine()

    first = engine.evaluate(projection)
    second = engine.evaluate(projection)

    assert first == second
    assert [item.rule_id for item in first] == [
        "BLOCKER_OPEN",
        "AUTHORITY_MISSING",
    ]
    assert all(item.reason for item in first)
    assert all(item.explanation for item in first)


def test_attention_ranking_does_not_create_decision_state() -> None:
    items = AttentionEngine().evaluate(
        make_projection(payload={"decision_pending": True})
    )

    assert len(items) == 1
    item = items[0]
    assert item.attention_class is AttentionClass.DECISION_PENDING
    assert not hasattr(item, "decision")
    assert not hasattr(item, "authorized")


def test_attention_tables_are_registered() -> None:
    assert AttentionItemModel.__tablename__ == "attention_items"
    assert AttentionProjectionRefModel.__tablename__ == "attention_projection_refs"
    assert "attention_items" in Base.metadata.tables
    assert "attention_projection_refs" in Base.metadata.tables
