package reisos.command

import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertTrue
import reisos.command.adapters.*
import reisos.command.contracts.*
import reisos.command.fixtures.SyntheticFixtures
import reisos.command.ui_state.UiState
import reisos.command.ui_state.mapCollectionState

class ContractChecks {
    @Test
    fun emptyRequiresCompleteCollection() {
        val state = mapCollectionState<OperationProjection>(emptyList(), CompletenessState.COMPLETE, FreshnessState.CURRENT)
        assertIs<UiState.Empty>(state)
    }

    @Test
    fun partialNeverCollapsesToEmpty() {
        val state = mapCollectionState<OperationProjection>(emptyList(), CompletenessState.PARTIAL, FreshnessState.CURRENT)
        assertIs<UiState.Partial<List<OperationProjection>>>(state)
    }

    @Test
    fun unknownFreshnessNeverRendersCurrentContent() {
        val state = mapCollectionState(SyntheticFixtures.partialOperations.items, CompletenessState.COMPLETE, FreshnessState.UNKNOWN)
        assertIs<UiState.Unknown>(state)
    }

    @Test
    fun missingGenerationCreatesPartialOcsState() {
        assertIs<UiState.Partial<*>>(adaptOcsProjection(SyntheticFixtures.ocsMissingGeneration))
    }

    @Test
    fun unknownGraphRelationTriggersCanonicalHold() {
        assertTrue(graphHasCanonicalRelationHold(SyntheticFixtures.graphUnknownEdge))
    }

    @Test
    fun executedReceiptWithoutReadbackIsNotVerified() {
        assertFalse(receiptIsVerified(SyntheticFixtures.receiptWithoutReadback, null))
    }

    @Test
    fun recoveryReadyRequiresEvidence() {
        val noEvidence = SyntheticFixtures.ocsOperationallyBound.copy(recoveryReady = true)
        assertFalse(canRenderRecoveryReady(noEvidence))
    }

    @Test
    fun progressWithoutSourceIsNotDisplayableAsPercent() {
        assertFalse(canRenderProgressPercent(SyntheticFixtures.operationActiveUnknownProgress))
    }

    @Test
    fun syntheticFixtureNeverClaimsRealSource() {
        assertTrue(SyntheticFixtures.institutionCurrentComplete.envelope.synthetic.isSynthetic)
        assertTrue(SyntheticFixtures.institutionCurrentComplete.envelope.synthetic.dataClass == DataClass.SYNTHETIC_UI_FIXTURE)
    }
}