package reisos.command.app

enum class DecisionStage {
    PROPOSED,
    AUTHORIZED,
    EXECUTED,
    VERIFIED,
    ASSURED,
    HOLD,
    DENY,
}

data class DecisionTransition(
    val from: DecisionStage,
    val to: DecisionStage,
    val evidenceRef: String? = null,
    val authorityRef: String? = null,
    val readbackRef: String? = null,
)

object DecisionLifecycle {
    private val allowed = setOf(
        DecisionStage.PROPOSED to DecisionStage.AUTHORIZED,
        DecisionStage.PROPOSED to DecisionStage.HOLD,
        DecisionStage.PROPOSED to DecisionStage.DENY,
        DecisionStage.AUTHORIZED to DecisionStage.EXECUTED,
        DecisionStage.AUTHORIZED to DecisionStage.HOLD,
        DecisionStage.EXECUTED to DecisionStage.VERIFIED,
        DecisionStage.EXECUTED to DecisionStage.HOLD,
        DecisionStage.VERIFIED to DecisionStage.ASSURED,
        DecisionStage.VERIFIED to DecisionStage.HOLD,
    )

    fun validateTransition(transition: DecisionTransition): List<String> = buildList {
        if ((transition.from to transition.to) !in allowed) {
            add("illegal_transition:${transition.from}->${transition.to}")
        }
        if (transition.to == DecisionStage.AUTHORIZED && transition.authorityRef.isNullOrBlank()) {
            add("authorization_without_authority_ref")
        }
        if (transition.to == DecisionStage.VERIFIED && transition.readbackRef.isNullOrBlank()) {
            add("verification_without_readback")
        }
        if (transition.to == DecisionStage.ASSURED && transition.evidenceRef.isNullOrBlank()) {
            add("assurance_without_evidence")
        }
    }

    fun validatePath(path: List<DecisionTransition>): List<String> = buildList {
        if (path.isEmpty()) add("decision_path_empty")
        path.forEachIndexed { index, transition ->
            addAll(validateTransition(transition))
            val next = path.getOrNull(index + 1)
            if (next != null && transition.to != next.from) {
                add("decision_path_discontinuity:${transition.to}->${next.from}")
            }
        }
    }

    val canonicalHappyPath = listOf(
        DecisionTransition(
            from = DecisionStage.PROPOSED,
            to = DecisionStage.AUTHORIZED,
            authorityRef = "fixture-authority-ref",
        ),
        DecisionTransition(
            from = DecisionStage.AUTHORIZED,
            to = DecisionStage.EXECUTED,
        ),
        DecisionTransition(
            from = DecisionStage.EXECUTED,
            to = DecisionStage.VERIFIED,
            readbackRef = "fixture-readback-ref",
        ),
        DecisionTransition(
            from = DecisionStage.VERIFIED,
            to = DecisionStage.ASSURED,
            evidenceRef = "fixture-assurance-evidence",
        ),
    )
}
