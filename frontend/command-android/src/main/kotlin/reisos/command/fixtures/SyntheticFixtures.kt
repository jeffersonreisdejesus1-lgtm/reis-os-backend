package reisos.command.fixtures

import reisos.command.contracts.*

private const val ORG = "REIS-OS"
private const val PROJECTED = "2026-09-07T00:00:00Z"

private fun envelope(
    id: String,
    type: String,
    freshness: FreshnessState = FreshnessState.CURRENT,
    completeness: CompletenessState = CompletenessState.COMPLETE,
    epistemic: EpistemicState = EpistemicState.NOT_PROVEN,
) = CommandResourceEnvelope(
    schemaVersion = "command-preliminary-v1",
    resourceType = type,
    resourceId = id,
    organizationId = ORG,
    projectedAt = PROJECTED,
    projectionVersion = "fixture-v1",
    freshness = Freshness(freshness),
    completeness = Completeness(completeness),
    epistemicState = epistemic,
    synthetic = SyntheticMetadata(true, DataClass.SYNTHETIC_UI_FIXTURE),
)

object SyntheticFixtures {
    val institutionCurrentComplete = InstitutionProjection(
        institutionId = ORG,
        canonicalName = "REIS OS",
        institutionalState = "SYNTHETIC_CURRENT",
        activeMissions = 3,
        holds = 1,
        pendingFounderDecisions = 1,
        envelope = envelope("institution-current", "InstitutionProjection", epistemic = EpistemicState.NOT_PROVEN),
    )

    val institutionStalePartial = InstitutionProjection(
        institutionId = ORG,
        canonicalName = "REIS OS",
        institutionalState = "SYNTHETIC_STALE",
        envelope = envelope(
            "institution-stale-partial",
            "InstitutionProjection",
            freshness = FreshnessState.STALE,
            completeness = CompletenessState.PARTIAL,
        ),
    )

    val ocsOperationallyBound = OCSProjection(
        ocsId = "REISOS::INST::IRIS::001",
        canonicalName = "ÍRIS",
        profileRef = "fixture-profile",
        availabilityState = AvailabilityState.OPERATIONALLY_BOUND,
        currentInstanceId = "fixture-instance-iris",
        generation = 1,
        missionId = "fixture-mission",
        recoveryReady = false,
        chatAddressable = true,
        envelope = envelope("ocs-iris", "OCSProjection"),
    )

    val ocsMissingGeneration = ocsOperationallyBound.copy(
        currentInstanceId = "fixture-instance-without-generation",
        generation = null,
        envelope = envelope("ocs-partial", "OCSProjection", completeness = CompletenessState.PARTIAL),
    )

    val operationActiveUnknownProgress = OperationProjection(
        operationId = "fixture-operation-active",
        missionId = "fixture-mission",
        title = "Synthetic active operation",
        ownerOcsId = "REISOS::INST::IRIS::001",
        lifecycleState = OperationLifecycle.ACTIVE,
        progress = ProgressValue(null, ProgressBasis.UNKNOWN),
        envelope = envelope("operation-active", "OperationProjection"),
    )

    val operationClosedNotAssured = operationActiveUnknownProgress.copy(
        operationId = "fixture-operation-closed",
        lifecycleState = OperationLifecycle.CLOSED,
        envelope = envelope("operation-closed", "OperationProjection", epistemic = EpistemicState.VERIFIED),
    )

    val gatePassWithReservations = GateProjection(
        gateId = "fixture-gate",
        gateType = "EXPERIENCE",
        objectRef = "fixture-object",
        status = GateStatus.PASS_WITH_RESERVATIONS,
        envelope = envelope("gate-pass-reservations", "GateProjection", epistemic = EpistemicState.PASS),
    )

    val receiptWithoutReadback = CommandReceipt(
        receiptId = "fixture-receipt",
        operationRef = "fixture-operation",
        requestedEffect = "fixture-effect",
        reportedEffect = "fixture-reported-effect",
        executionState = ReceiptExecutionState.EXECUTED,
        correlationId = "fixture-correlation",
        envelope = envelope("receipt-no-readback", "CommandReceipt", epistemic = EpistemicState.EXECUTED),
    )

    val readbackMismatch = ReadbackRecord(
        readbackId = "fixture-readback-mismatch",
        objectRef = "fixture-object",
        receiptRef = receiptWithoutReadback.receiptId,
        comparison = ReadbackComparison.MISMATCH,
        envelope = envelope("readback-mismatch", "ReadbackRecord", epistemic = EpistemicState.HOLD),
    )

    val evidenceInvalid = EvidenceRecord(
        evidenceId = "fixture-evidence-invalid",
        evidenceType = "SYNTHETIC",
        objectRef = "fixture-object",
        sourceRef = "fixture-source",
        validationState = EvidenceValidationState.INVALID,
        envelope = envelope("evidence-invalid", "EvidenceRecord", epistemic = EpistemicState.NOT_PROVEN),
    )

    val graphUnknownEdge = GraphProjection(
        graphId = "fixture-graph",
        graphType = GraphType.CAUSAL,
        nodes = listOf(
            GraphNode("a", "EVENT", "A", null, "UNKNOWN", "fixture-source-a"),
            GraphNode("b", "EVENT", "B", null, "UNKNOWN", "fixture-source-b"),
        ),
        edges = listOf(GraphEdge("edge-unknown", "a", "b", GraphRelation.UNKNOWN_EDGE_TYPE, "fixture-source-edge")),
        snapshotRef = "fixture-snapshot",
        envelope = envelope("graph-unknown-edge", "GraphProjection", epistemic = EpistemicState.HOLD),
    )

    val systemAvailableButStale = SystemHealthProjection(
        componentId = "fixture-command",
        componentType = "COMMAND",
        availability = Availability.AVAILABLE,
        health = Health.HEALTHY,
        freshness = Freshness(FreshnessState.STALE),
        envelope = envelope("system-stale", "SystemHealthProjection", freshness = FreshnessState.STALE),
    )

    val systemHealthyUnknownFreshness = systemAvailableButStale.copy(
        componentId = "fixture-command-unknown-freshness",
        freshness = Freshness(FreshnessState.UNKNOWN),
        envelope = envelope("system-unknown-freshness", "SystemHealthProjection", freshness = FreshnessState.UNKNOWN),
    )

    val intentDeny = CommandIntentDecision(
        intentId = "fixture-intent-deny",
        decision = IntentDecision.DENY,
        reason = "Synthetic denial",
        receiptExpected = false,
        readbackRequired = false,
    )

    val intentHold = intentDeny.copy(intentId = "fixture-intent-hold", decision = IntentDecision.HOLD, reason = "Synthetic hold")

    val emptyCompleteOperations = CollectionEnvelope<OperationProjection>(
        items = emptyList(),
        snapshotRef = "fixture-empty-snapshot",
        projectedAt = PROJECTED,
        completeness = CompletenessState.COMPLETE,
    )

    val partialOperations = CollectionEnvelope(
        items = listOf(operationActiveUnknownProgress),
        nextCursor = "fixture-next",
        hasMore = true,
        snapshotRef = "fixture-partial-snapshot",
        projectedAt = PROJECTED,
        completeness = CompletenessState.PARTIAL,
    )
}