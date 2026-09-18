from app.cognitive_validation import CausalMemoryStore, MemoryAugmentedDecisionEngine


def _trained_memory() -> CausalMemoryStore:
    return (
        CausalMemoryStore()
        .remember(key="task:alpha", value=0.5, source_trace_id="trace-alpha-t0")
        .remember(key="task:beta", value=-0.7, source_trace_id="trace-beta-t0")
    )


def test_ab2_relevant_memory_changes_future_decision():
    memory = _trained_memory()
    engine = MemoryAugmentedDecisionEngine()

    with_memory = engine.decide(stimulus=-0.2, memory_key="task:alpha", memory=memory)
    without_memory = engine.decide(
        stimulus=-0.2,
        memory_key="task:alpha",
        memory=CausalMemoryStore(),
    )

    assert with_memory.action == 1
    assert without_memory.action == 0
    assert with_memory.memory_value == 0.5
    assert with_memory.memory_source_trace_id == "trace-alpha-t0"


def test_ab2_specific_relevant_memory_ablation_removes_learned_effect():
    memory = _trained_memory()
    ablated = memory.ablate("task:alpha")
    engine = MemoryAugmentedDecisionEngine()

    treatment = engine.decide(stimulus=-0.2, memory_key="task:alpha", memory=memory)
    control = engine.decide(stimulus=-0.2, memory_key="task:alpha", memory=ablated)

    assert treatment.action == 1
    assert control.action == 0
    assert control.memory_value == 0.0
    assert control.memory_source_trace_id is None


def test_ab2_unrelated_memory_ablation_preserves_relevant_effect():
    memory = _trained_memory()
    ablated = memory.ablate("task:beta")
    engine = MemoryAugmentedDecisionEngine()

    treatment = engine.decide(stimulus=-0.2, memory_key="task:alpha", memory=memory)
    control = engine.decide(stimulus=-0.2, memory_key="task:alpha", memory=ablated)

    assert treatment == control
    assert control.action == 1


def test_ab2_memory_effect_is_deterministically_reproducible():
    memory = _trained_memory()
    engine = MemoryAugmentedDecisionEngine()

    results = [
        engine.decide(stimulus=-0.2, memory_key="task:alpha", memory=memory)
        for _ in range(10)
    ]

    assert all(item == results[0] for item in results)
    assert results[0].action == 1


def test_ab2_memory_provenance_is_required_fail_closed():
    memory = CausalMemoryStore()

    try:
        memory.remember(key="task:alpha", value=0.5, source_trace_id="")
    except ValueError as exc:
        assert "source_trace_id" in str(exc)
    else:
        raise AssertionError("memory without provenance must fail closed")


def test_ab2_memory_revision_advances_on_same_key_update():
    memory = CausalMemoryStore().remember(
        key="task:alpha", value=0.3, source_trace_id="trace-1"
    )
    memory = memory.remember(
        key="task:alpha", value=0.6, source_trace_id="trace-2"
    )

    record = memory.get_record("task:alpha")
    assert record is not None
    assert record.revision == 2
    assert record.value == 0.6
    assert record.source_trace_id == "trace-2"
