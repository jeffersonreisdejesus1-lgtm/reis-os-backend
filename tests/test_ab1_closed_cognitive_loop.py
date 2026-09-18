from app.cognitive_validation import ClosedCognitiveLoop, CognitiveState


def test_ab1_prior_state_changes_future_processing_after_experience():
    loop = ClosedCognitiveLoop(learning_rate=0.5)
    initial = CognitiveState()

    t0 = loop.cycle(
        initial,
        stimulus=-0.2,
        expected_action=1,
        apply_state_update=True,
    )
    t1 = loop.decide(t0.after, stimulus=-0.2)

    assert t0.decision.action == 0
    assert t0.observation.residual == 1
    assert t0.after.revision == 1
    assert t0.after.bias == 0.5
    assert t1.action == 1


def test_ab1_ablation_removes_future_behavior_change():
    loop = ClosedCognitiveLoop(learning_rate=0.5)
    initial = CognitiveState()

    learned = loop.cycle(
        initial,
        stimulus=-0.2,
        expected_action=1,
        apply_state_update=True,
    )
    ablated = loop.cycle(
        initial,
        stimulus=-0.2,
        expected_action=1,
        apply_state_update=False,
    )

    learned_t1 = loop.decide(learned.after, stimulus=-0.2)
    ablated_t1 = loop.decide(ablated.after, stimulus=-0.2)

    assert learned_t1.action == 1
    assert ablated_t1.action == 0
    assert learned.after != initial
    assert ablated.after == initial


def test_ab1_causal_chain_is_explicit_and_traceable():
    loop = ClosedCognitiveLoop(learning_rate=0.25)
    state = CognitiveState()

    trace = loop.cycle(
        state,
        stimulus=-0.1,
        expected_action=1,
        apply_state_update=True,
    )

    assert trace.before == state
    assert trace.decision.state_revision == state.revision
    assert trace.observation.observed_action == trace.decision.action
    assert trace.observation.residual == 1
    assert trace.after.revision == state.revision + 1
    assert trace.state_update_applied is True


def test_ab1_invalid_feedback_target_fails_closed():
    loop = ClosedCognitiveLoop()
    decision = loop.decide(CognitiveState(), stimulus=0.0)

    try:
        loop.observe(decision, expected_action=2)
    except ValueError as exc:
        assert "expected_action must be 0 or 1" in str(exc)
    else:
        raise AssertionError("invalid feedback target must fail closed")
