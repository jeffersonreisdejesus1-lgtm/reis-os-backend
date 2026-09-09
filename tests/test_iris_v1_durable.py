import json
import sqlite3
from dataclasses import replace

import pytest

from app.iris_v1 import (
    DecisionStatus,
    EvidenceFreshness,
    GovernorLease,
    GovernanceRequest,
    IRIS_DERIVATION_REF,
    IrisV1Bindings,
    IrisV1DurableRuntime,
    IrisV1InvariantError,
    derived_governor_specs,
)

MISSION = "REIS-OS-OCS-REFACTOR-V1-IRIS-001"


def durable(path):
    rt = IrisV1DurableRuntime(
        mission_id=MISSION,
        bindings=IrisV1Bindings.materialized(),
        derivation_ref=IRIS_DERIVATION_REF,
        database_path=path,
    )
    if not rt._governors:
        for spec in derived_governor_specs():
            rt.register_governor(spec)
        rt.bind_lease(GovernorLease(
            lease_id="lease:d:1",
            mission_id=MISSION,
            governor_id="GOV-IRIS-01",
            scope=("NS_IRIS_DESIGN_WORKING",),
            generation=1,
            valid_from=100.0,
            expires_at=500.0,
        ))
    return rt


def request(**changes):
    base = GovernanceRequest(
        request_id="req:d:1",
        mission_id=MISSION,
        governor_id="GOV-IRIS-01",
        operation="SET_PERCEPTION_INTERACTION_STATE",
        namespace="NS_IRIS_DESIGN_WORKING",
        mutation={"hierarchy": "clear"},
        expected_state_version=0,
        lease_id="lease:d:1",
        generation=1,
        idempotency_key="idem:d:1",
        evidence_freshness=EvidenceFreshness.CURRENT,
    )
    return replace(base, **changes)


def _rewrite_latest_snapshot(db, mutate):
    with sqlite3.connect(db) as connection:
        row = connection.execute(
            "SELECT seq, snapshot_json FROM iris_v1_snapshot_journal WHERE mission_id=? ORDER BY seq DESC LIMIT 1",
            (MISSION,),
        ).fetchone()
        payload = json.loads(row[1])
        mutate(payload)
        forged_hash = IrisV1DurableRuntime._snapshot_hash(payload)
        connection.execute(
            "UPDATE iris_v1_snapshot_journal SET snapshot_json=?, snapshot_hash=? WHERE seq=?",
            (json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")), forged_hash, row[0]),
        )
        connection.commit()


def test_restart_preserves_state_and_revalidates_local_contracts(tmp_path):
    db = tmp_path / "iris.sqlite"
    rt = durable(db)
    assert rt.execute(request(), now=110.0).status is DecisionStatus.ACCEPTED
    assert rt.verify_snapshot_chain()

    restarted = durable(db)
    assert restarted.state["NS_IRIS_DESIGN_WORKING"]["hierarchy"] == "clear"
    assert restarted.identity_state_root == "EC-IRIS-GENERALIST-EVO-001 + IRIS_STATE.json"
    replay = restarted.execute(request(), now=110.0)
    assert replay.idempotent_replay is True


def test_durable_restore_rejects_forged_governor_even_with_rehashed_snapshot(tmp_path):
    db = tmp_path / "iris.sqlite"
    rt = durable(db)
    with sqlite3.connect(db) as connection:
        row = connection.execute(
            "SELECT seq, snapshot_json FROM iris_v1_snapshot_journal WHERE mission_id=? ORDER BY seq DESC LIMIT 1",
            (MISSION,),
        ).fetchone()
        payload = json.loads(row[1])
        payload["governors"][0]["role"] = "AUTHORITY_ROOT"
        forged_hash = rt._snapshot_hash(payload)
        connection.execute(
            "UPDATE iris_v1_snapshot_journal SET snapshot_json=?, snapshot_hash=? WHERE seq=?",
            (json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")), forged_hash, row[0]),
        )
        connection.commit()

    with pytest.raises(IrisV1InvariantError, match="CONTRACT_NOT_CANONICAL"):
        durable(db)


def test_durable_restore_rejects_omitted_governor_even_with_rehashed_snapshot(tmp_path):
    db = tmp_path / "iris.sqlite"
    durable(db)

    def omit_governor(payload):
        payload["governors"] = [
            raw for raw in payload["governors"]
            if raw["governor_id"] != "GOV-IRIS-04"
        ]

    _rewrite_latest_snapshot(db, omit_governor)

    with pytest.raises(IrisV1InvariantError, match="GOVERNOR_ROSTER_INCOMPLETE"):
        durable(db)


def test_durable_restore_rejects_omitted_generation_owner_even_with_rehashed_snapshot(tmp_path):
    db = tmp_path / "iris.sqlite"
    durable(db)

    def omit_generation_owner(payload):
        payload["generation"].pop("GOV-IRIS-04")

    _rewrite_latest_snapshot(db, omit_generation_owner)

    with pytest.raises(IrisV1InvariantError, match="GENERATION_OWNER_SET_MISMATCH"):
        durable(db)


def test_snapshot_tamper_without_rehash_is_rejected(tmp_path):
    db = tmp_path / "iris.sqlite"
    durable(db)
    with sqlite3.connect(db) as connection:
        row = connection.execute(
            "SELECT seq, snapshot_json FROM iris_v1_snapshot_journal WHERE mission_id=? ORDER BY seq DESC LIMIT 1",
            (MISSION,),
        ).fetchone()
        payload = json.loads(row[1])
        payload["identity_state_root"] = "FORGED"
        connection.execute(
            "UPDATE iris_v1_snapshot_journal SET snapshot_json=? WHERE seq=?",
            (json.dumps(payload), row[0]),
        )
        connection.commit()
    with pytest.raises(IrisV1InvariantError, match="SNAPSHOT_INTEGRITY_FAILURE"):
        durable(db)


def test_concurrent_stale_writer_fails_closed_and_reconciles_to_durable_head(tmp_path):
    db = tmp_path / "iris.sqlite"
    rt1 = durable(db)
    rt2 = durable(db)
    assert rt1.execute(request(), now=110.0).status is DecisionStatus.ACCEPTED

    with pytest.raises(IrisV1InvariantError, match="DURABLE_STALE_WRITER"):
        rt2.execute(request(request_id="req:d:stale", idempotency_key="idem:d:stale"), now=110.0)
    assert rt2.state["NS_IRIS_DESIGN_WORKING"]["hierarchy"] == "clear"
    assert rt2.state_version == 1


def test_restart_rejects_binding_or_derivation_substitution_at_constructor(tmp_path):
    db = tmp_path / "iris.sqlite"
    durable(db)
    refs = dict(IrisV1Bindings.materialized().refs)
    refs["R5_R7_BINDING_REF"] = "fake"
    with pytest.raises(IrisV1InvariantError, match="BINDING_REF_MISMATCH"):
        IrisV1DurableRuntime(
            mission_id=MISSION,
            bindings=IrisV1Bindings(refs),
            derivation_ref=IRIS_DERIVATION_REF,
            database_path=db,
        )
