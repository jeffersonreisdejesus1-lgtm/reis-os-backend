package reisos.command

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import reisos.command.app.DecisionLifecycle
import reisos.command.app.DecisionStage
import reisos.command.app.DecisionTransition

class DecisionLifecycleChecks {
    @Test
    fun canonicalDecisionPathIsContinuousAndEvidenceBound() {
        assertEquals(emptyList(), DecisionLifecycle.validatePath(DecisionLifecycle.canonicalHappyPath))
    }

    @Test
    fun executedCannotSkipDirectlyToAssured() {
        val failures = DecisionLifecycle.validateTransition(
            DecisionTransition(
                from = DecisionStage.EXECUTED,
                to = DecisionStage.ASSURED,
                evidenceRef = "fixture-evidence",
            ),
        )
        assertTrue(failures.any { it.startsWith("illegal_transition:") })
    }

    @Test
    fun verifiedRequiresReadback() {
        val failures = DecisionLifecycle.validateTransition(
            DecisionTransition(
                from = DecisionStage.EXECUTED,
                to = DecisionStage.VERIFIED,
            ),
        )
        assertTrue("verification_without_readback" in failures)
    }

    @Test
    fun authorizationRequiresAuthorityReference() {
        val failures = DecisionLifecycle.validateTransition(
            DecisionTransition(
                from = DecisionStage.PROPOSED,
                to = DecisionStage.AUTHORIZED,
            ),
        )
        assertTrue("authorization_without_authority_ref" in failures)
    }

    @Test
    fun assuranceRequiresEvidence() {
        val failures = DecisionLifecycle.validateTransition(
            DecisionTransition(
                from = DecisionStage.VERIFIED,
                to = DecisionStage.ASSURED,
            ),
        )
        assertTrue("assurance_without_evidence" in failures)
    }

    @Test
    fun discontinuousLifecycleIsRejected() {
        val failures = DecisionLifecycle.validatePath(
            listOf(
                DecisionTransition(
                    DecisionStage.PROPOSED,
                    DecisionStage.AUTHORIZED,
                    authorityRef = "fixture-authority-ref",
                ),
                DecisionTransition(
                    DecisionStage.EXECUTED,
                    DecisionStage.VERIFIED,
                    readbackRef = "fixture-readback-ref",
                ),
            ),
        )
        assertTrue(failures.any { it.startsWith("decision_path_discontinuity:") })
    }
}
