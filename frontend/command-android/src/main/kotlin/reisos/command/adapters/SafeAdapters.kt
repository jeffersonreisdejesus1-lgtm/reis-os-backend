package reisos.command.adapters

import reisos.command.contracts.*
import reisos.command.ui_state.UiState
import reisos.command.ui_state.mapCollectionState

data class OcsCardModel(
    val ocsId: String,
    val name: String,
    val availability: AvailabilityState,
    val instanceId: String?,
    val generation: Int?,
    val freshness: FreshnessState,
    val completeness: CompletenessState,
)

fun adaptOcsProjection(input: OCSProjection): UiState<OcsCardModel> {
    if (input.currentInstanceId != null && input.generation == null) {
        return UiState.Partial(
            OcsCardModel(
                input.ocsId,
                input.canonicalName,
                input.availabilityState,
                input.currentInstanceId,
                null,
                input.envelope.freshness.state,
                CompletenessState.PARTIAL,
            ),
            missingFields = listOf("generation"),
        )
    }

    val model = OcsCardModel(
        input.ocsId,
        input.canonicalName,
        input.availabilityState,
        input.currentInstanceId,
        input.generation,
        input.envelope.freshness.state,
        input.envelope.completeness.state,
    )

    return when (input.envelope.freshness.state) {
        FreshnessState.STALE -> UiState.Stale(model, input.envelope.freshness.reason)
        FreshnessState.UNKNOWN -> UiState.Unknown("OCS freshness unknown")
        FreshnessState.CURRENT -> when (input.envelope.completeness.state) {
            CompletenessState.COMPLETE -> UiState.Content(model, FreshnessState.CURRENT, CompletenessState.COMPLETE)
            CompletenessState.PARTIAL -> UiState.Partial(model, input.envelope.completeness.missingFields)
            CompletenessState.UNKNOWN -> UiState.Unknown("OCS completeness unknown")
        }
    }
}

fun adaptOperations(input: CollectionEnvelope<OperationProjection>, freshness: FreshnessState): UiState<List<OperationProjection>> =
    mapCollectionState(input.items, input.completeness, freshness)

fun graphHasCanonicalRelationHold(graph: GraphProjection): Boolean =
    graph.edges.any { it.relation == GraphRelation.UNKNOWN_EDGE_TYPE }

fun receiptIsVerified(receipt: CommandReceipt, readback: ReadbackRecord?): Boolean =
    receipt.executionState == ReceiptExecutionState.EXECUTED &&
        readback?.comparison == ReadbackComparison.MATCH &&
        readback.envelope.epistemicState in setOf(EpistemicState.VERIFIED, EpistemicState.ASSURED)

fun canRenderRecoveryReady(ocs: OCSProjection): Boolean =
    ocs.recoveryReady == true && ocs.envelope.evidenceRefs.isNotEmpty()

fun canRenderProgressPercent(operation: OperationProjection): Boolean =
    operation.progress.value != null &&
        operation.progress.basis != ProgressBasis.UNKNOWN &&
        operation.progress.sourceRefs.isNotEmpty()