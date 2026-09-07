package reisos.command

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertTrue
import reisos.command.adapters.adaptOcsProjection
import reisos.command.adapters.adaptOperations
import reisos.command.adapters.canRenderProgressPercent
import reisos.command.adapters.graphHasCanonicalRelationHold
import reisos.command.adapters.receiptIsVerified
import reisos.command.contracts.FreshnessState
import reisos.command.fixtures.SyntheticFixtures
import reisos.command.navigation.CommandRoute
import reisos.command.navigation.NavigationContext
import reisos.command.navigation.primaryNavigation
import reisos.command.ui_state.UiState

class LongitudinalFlowChecks {
    @Test
    fun syntheticCommandPathPreservesEpistemicAndAuthorityBoundariesEndToEnd() {
        // S0: institution/home projection is synthetic and not proof of runtime truth.
        assertTrue(SyntheticFixtures.institutionCurrentComplete.envelope.synthetic.isSynthetic)

        // S3 -> S4: OCS directory/detail adapts incomplete instance state as PARTIAL, never complete.
        val ocsState = adaptOcsProjection(SyntheticFixtures.ocsMissingGeneration)
        val partial = assertIs<UiState.Partial<*>>(ocsState)
        assertTrue(partial.missingFields.contains("generation"))

        // S1 -> S2: unknown progress cannot become a fabricated percentage.
        assertFalse(canRenderProgressPercent(SyntheticFixtures.operationActiveUnknownProgress))

        // Collection semantics: complete-empty is EMPTY; partial is never collapsed to complete-empty.
        val emptyState = adaptOperations(SyntheticFixtures.emptyCompleteOperations, FreshnessState.CURRENT)
        assertIs<UiState.Empty>(emptyState)
        val partialOperations = adaptOperations(SyntheticFixtures.partialOperations, FreshnessState.CURRENT)
        assertIs<UiState.Partial<*>>(partialOperations)

        // S5: unknown graph relation is held rather than accepted as canonical causal semantics.
        assertTrue(graphHasCanonicalRelationHold(SyntheticFixtures.graphUnknownEdge))

        // Receipt lifecycle: EXECUTED without matching readback is never VERIFIED.
        assertFalse(receiptIsVerified(SyntheticFixtures.receiptWithoutReadback, null))
        assertFalse(receiptIsVerified(SyntheticFixtures.receiptWithoutReadback, SyntheticFixtures.readbackMismatch))

        // Navigation spans the primary longitudinal surfaces and carries context without authority.
        assertEquals(
            listOf("S0_HOME", "S1_OPERATIONS", "S3_OCS_DIRECTORY", "S7_EVOLUTION", "S9_CONVERSATION"),
            primaryNavigation.map { it.id },
        )
        val context = NavigationContext(objectRef = "fixture-object", contextRefs = listOf("fixture-evidence"))
        assertEquals("fixture-object", context.objectRef)
        assertEquals(CommandRoute.OperationDetail("fixture-operation-active").id, "S2_OPERATION_DETAIL")

        // Failure/uncertainty fixtures remain explicitly non-authoritative.
        assertEquals(FreshnessState.STALE, SyntheticFixtures.systemAvailableButStale.freshness.state)
        assertEquals(FreshnessState.UNKNOWN, SyntheticFixtures.systemHealthyUnknownFreshness.freshness.state)
        assertFalse(SyntheticFixtures.intentDeny.receiptExpected)
    }
}
