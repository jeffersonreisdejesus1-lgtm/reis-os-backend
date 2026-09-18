from app.cognitive_validation.distributed_integrated_cognition import (
    DistributedIntegratedCognition,
    OCS_IDS,
)


def test_exactly_eleven_distinct_ocs_runtime_bindings():
    runtime = DistributedIntegratedCognition()
    assert tuple(runtime.actors) == OCS_IDS
    assert len({actor.logical_runtime_id for actor in runtime.actors.values()}) == 11
    assert len({actor.instance_id for actor in runtime.actors.values()}) == 11


def test_all_eleven_contribute_to_integrated_cognition():
    runtime = DistributedIntegratedCognition()
    result = runtime.run("planning")
    assert result.active_actors == OCS_IDS
    assert set(result.contribution_by_actor) == set(OCS_IDS)
    assert len(result.trace) == 10
    assert result.aggregate_score > 0
    assert result.hidden_central_mind is False


def test_memory_is_namespaced_per_ocs():
    runtime = DistributedIntegratedCognition()
    runtime.run("memory")
    snapshot = runtime.memory_snapshot()
    assert all(snapshot[ocs]["memory"] == 1 for ocs in OCS_IDS)
    snapshot["NOESIS"]["memory"] = 999
    assert runtime.actors["DEDALA"].local_memory["memory"] == 1


def test_governed_bus_is_the_only_cross_actor_causal_trace():
    runtime = DistributedIntegratedCognition()
    result = runtime.run("causal")
    assert all(message.sender != message.receiver for message in result.trace)
    assert [message.ordinal for message in result.trace] == list(range(1, 11))
    assert {message.task_family for message in result.trace} == {"causal"}


def test_actor_ablation_causes_predictable_degradation():
    full = DistributedIntegratedCognition().run("ablation")
    reduced = DistributedIntegratedCognition().run("ablation", ablate={"METIS"})
    assert len(reduced.active_actors) == 10
    assert "METIS" not in reduced.contribution_by_actor
    assert reduced.aggregate_score < full.aggregate_score


def test_killing_one_actor_does_not_stop_remaining_actors():
    runtime = DistributedIntegratedCognition()
    runtime.kill("SOFIA")
    result = runtime.run("failure-isolation")
    assert "SOFIA" not in result.active_actors
    assert len(result.active_actors) == 10
    assert all(runtime.actors[ocs].alive for ocs in OCS_IDS if ocs != "SOFIA")


def test_recovery_advances_generation_without_identity_drift():
    runtime = DistributedIntegratedCognition()
    before = runtime.actors["AGORA"]
    original_ocs_id = before.ocs_id
    original_runtime_id = before.logical_runtime_id
    runtime.kill("AGORA")
    runtime.revive("AGORA")
    after = runtime.actors["AGORA"]
    assert after.ocs_id == original_ocs_id
    assert after.logical_runtime_id == original_runtime_id
    assert after.generation == 2
    assert after.instance_id.endswith("::g2")


def test_deterministic_reproducibility_for_same_task():
    first = DistributedIntegratedCognition().run("deterministic")
    second = DistributedIntegratedCognition().run("deterministic")
    assert first.contribution_by_actor == second.contribution_by_actor
    assert first.aggregate_score == second.aggregate_score
