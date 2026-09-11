from __future__ import annotations

import pytest

from app.distributed_runtime.pipeline import NoesisDedalaAgoraPipeline, PipelineEnvelope
from app.ocs_instances.contracts import BindingMaturity, InstanceBinding, InstanceStatus
from app.profile_bindings.profiles import get_profile


def active_binding(ocs_id: str, generation: int = 21) -> InstanceBinding:
    profile = get_profile(ocs_id)
    slug = {"NÓESIS": "noesis", "DÉDALA": "dedala", "ÁGORA": "agora"}[ocs_id]
    return InstanceBinding(
        binding_id=f"binding:dr3:{slug}:g{generation}",
        mission_id="mission:dr3-three-actor-pipeline",
        run_id=f"run:dr3:{slug}",
        organization_id="org:reis-os",
        ocs_id=ocs_id,
        profile_version=profile.version,
        profile_hash=f"profile-hash:{slug}",
        identity_binding_hash=f"identity-hash:{slug}",
        request_hash=f"request-hash:{slug}",
        maturity=BindingMaturity.OPERATIONALLY_BOUND_L1,
        host="dr3-local-process",
        capability="cognitive-physiology",
        lease_id=f"lease:dr3:{slug}",
        authority_ref=profile.authority_ref,
        scope=("dr3-causal-pipeline",),
        state_namespace=profile.state_namespace,
        memory_namespace=profile.memory_namespace,
        generation=generation,
        platform_instance_id=None,
        challenge_hash=f"challenge:{slug}",
        bootstrap_hash=f"bootstrap:{slug}",
        status=InstanceStatus.ACTIVE,
        version=1,
        predecessor_binding_id=None,
        checkpoint_version=0,
        checkpoint_hash=None,
        hazel_event_hash=None,
        idempotency_key=f"idem:dr3:{slug}",
        correlation_id="corr:dr3",
        causation_id=None,
        created_at=1.0,
        updated_at=1.0,
    )


def bindings() -> dict[str, InstanceBinding]:
    return {ocs: active_binding(ocs) for ocs in ("NÓESIS", "DÉDALA", "ÁGORA")}


def test_dr3_materializes_three_distinct_execution_contexts() -> None:
    runtime = NoesisDedalaAgoraPipeline(bindings())
    try:
        snapshots = runtime.start()
        assert len({s.pid for s in snapshots.values()}) == 3
        assert len({s.execution_context_id for s in snapshots.values()}) == 3
        assert len({s.failure_domain_id for s in snapshots.values()}) == 3
        assert len({s.state_namespace for s in snapshots.values()}) == 3
        assert len({s.memory_namespace for s in snapshots.values()}) == 3
    finally:
        runtime.stop_all()


def test_dr3_pipeline_has_causal_local_transformations() -> None:
    runtime = NoesisDedalaAgoraPipeline(bindings())
    try:
        runtime.start()
        receipts = runtime.execute({"mission": "qualify-three-actor-causality"})
        assert [r.target_ocs for r in receipts] == ["NÓESIS", "DÉDALA", "ÁGORA"]
        assert [r.transformation for r in receipts] == [
            "mission_framing",
            "architectural_review",
            "material_qualification",
        ]
        assert receipts[0].output_payload["noesis_framed"] is True
        assert receipts[1].output_payload["noesis_framed"] is True
        assert receipts[1].output_payload["dedala_reviewed"] is True
        assert receipts[2].output_payload["noesis_framed"] is True
        assert receipts[2].output_payload["dedala_reviewed"] is True
        assert receipts[2].output_payload["agora_qualified"] is True
        assert len({r.trace_id for r in receipts}) == 1
    finally:
        runtime.stop_all()


def test_dr3_each_actor_materially_changes_payload_hash() -> None:
    runtime = NoesisDedalaAgoraPipeline(bindings())
    try:
        runtime.start()
        receipts = runtime.execute({"seed": 1})
        for receipt in receipts:
            assert receipt.input_payload_hash != receipt.output_payload_hash
    finally:
        runtime.stop_all()


def test_dr3_rejects_stale_target_generation() -> None:
    runtime = NoesisDedalaAgoraPipeline(bindings())
    try:
        runtime.start()
        worker = runtime._workers["DÉDALA"]
        target = worker.health()
        stale = PipelineEnvelope(
            message_id="stale",
            mission_id="mission:stale",
            source_ocs="NÓESIS",
            source_instance_id="source",
            source_generation=target.generation,
            target_ocs="DÉDALA",
            target_expected_generation=target.generation - 1,
            input_payload_hash="x",
            payload={"x": 1},
            payload_hash="5041bf1f713df204784353e82f6a4a53549e4f1d7b3d7f0a7f5403a2f8f1b4f8",
            causation_id="root",
            trace_id="trace:stale",
        )
        with pytest.raises(RuntimeError, match="pipeline_stale_generation"):
            worker.process(stale)
    finally:
        runtime.stop_all()


def test_dr3_requires_exact_actor_set() -> None:
    incomplete = {"NÓESIS": active_binding("NÓESIS"), "DÉDALA": active_binding("DÉDALA")}
    with pytest.raises(PermissionError, match="dr3_requires_noesis_dedala_agora"):
        NoesisDedalaAgoraPipeline(incomplete)


def test_dr3_no_direct_cross_ocs_state_or_memory_api() -> None:
    runtime = NoesisDedalaAgoraPipeline(bindings())
    assert not hasattr(runtime, "write_other_state")
    assert not hasattr(runtime, "read_other_memory")
    assert not hasattr(runtime, "mutate_namespace")
