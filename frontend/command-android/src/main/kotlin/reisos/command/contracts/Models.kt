package reisos.command.contracts

/** Non-runtime UI-facing contract models only. */

enum class FreshnessState { CURRENT, STALE, UNKNOWN }
enum class CompletenessState { COMPLETE, PARTIAL, UNKNOWN }
enum class DataClass { REAL_SOURCE, SYNTHETIC_UI_FIXTURE }
enum class EpistemicState {
    UNKNOWN, NOT_PROVEN, PROPOSED, AUTHORIZED, REQUESTED, EXECUTED, VERIFIED, ASSURED,
    PASS, HOLD, DEGRADE, FAIL, DENY
}

data class Freshness(
    val state: FreshnessState,
    val ageSeconds: Long? = null,
    val maxAgeSeconds: Long? = null,
    val reason: String? = null,
)

data class Completeness(
    val state: CompletenessState,
    val missingFields: List<String> = emptyList(),
)

data class SyntheticMetadata(
    val isSynthetic: Boolean,
    val dataClass: DataClass,
)

data class CommandResourceEnvelope(
    val schemaVersion: String,
    val resourceType: String,
    val resourceId: String,
    val organizationId: String,
    val tenantId: String? = null,
    val sourceRefs: List<String> = emptyList(),
    val evidenceRefs: List<String> = emptyList(),
    val sourceObservedAt: String? = null,
    val projectedAt: String,
    val sourceVersion: String? = null,
    val projectionVersion: String,
    val freshness: Freshness,
    val completeness: Completeness,
    val epistemicState: EpistemicState,
    val synthetic: SyntheticMetadata,
)

data class InstitutionProjection(
    val institutionId: String,
    val canonicalName: String,
    val institutionalState: String,
    val currentPhase: String? = null,
    val activeMissions: Int? = null,
    val holds: Int? = null,
    val pendingFounderDecisions: Int? = null,
    val envelope: CommandResourceEnvelope,
)

enum class AvailabilityState {
    UNAVAILABLE, AVAILABLE_NATIVE_HOST_ONLY, PROFILE_BOUND, MISSION_BOUND, OPERATIONALLY_BOUND,
    RECOVERABLE, TEN_OCS_PROVEN, CHAT_ADDRESSABLE, INSTITUTIONALLY_AVAILABLE, UNKNOWN
}

data class OCSProjection(
    val ocsId: String,
    val canonicalName: String,
    val profileRef: String,
    val profileVersion: String? = null,
    val profileHash: String? = null,
    val authorityRef: String? = null,
    val stateNamespace: String? = null,
    val memoryNamespace: String? = null,
    val availabilityState: AvailabilityState,
    val currentInstanceId: String? = null,
    val generation: Int? = null,
    val missionId: String? = null,
    val recoveryReady: Boolean? = null,
    val chatAddressable: Boolean? = null,
    val lastCheckpointRef: String? = null,
    val lastReadbackRef: String? = null,
    val envelope: CommandResourceEnvelope,
)

enum class OperationLifecycle { PREPARED, ACTIVE, WAITING, BLOCKED, HOLD, RECOVERING, CLOSED, REVOKED, UNKNOWN }
enum class ProgressBasis { MEASURED, DERIVED, UNKNOWN }

data class ProgressValue(
    val value: Double? = null,
    val basis: ProgressBasis = ProgressBasis.UNKNOWN,
    val sourceRefs: List<String> = emptyList(),
)

data class OperationProjection(
    val operationId: String,
    val missionId: String,
    val title: String,
    val ownerOcsId: String,
    val participatingOcsIds: List<String> = emptyList(),
    val lifecycleState: OperationLifecycle,
    val progress: ProgressValue = ProgressValue(),
    val currentGateId: String? = null,
    val blockerRefs: List<String> = emptyList(),
    val receiptRefs: List<String> = emptyList(),
    val evidenceRefs: List<String> = emptyList(),
    val envelope: CommandResourceEnvelope,
)

enum class GateStatus { NOT_OPENED, PENDING, PASS, PASS_WITH_RESERVATIONS, HOLD, DEGRADE, FAIL, DENY, UNKNOWN }

data class GateProjection(
    val gateId: String,
    val gateType: String,
    val objectRef: String,
    val status: GateStatus,
    val evaluatorOcsId: String? = null,
    val evidenceRefs: List<String> = emptyList(),
    val founderActionRequired: Boolean = false,
    val founderDecisionRef: String? = null,
    val envelope: CommandResourceEnvelope,
)

enum class ReceiptExecutionState { REQUESTED, DISPATCHED, ACKNOWLEDGED, EXECUTED, FAILED, UNKNOWN }

data class CommandReceipt(
    val receiptId: String,
    val operationRef: String,
    val requestedEffect: String,
    val reportedEffect: String? = null,
    val executionState: ReceiptExecutionState,
    val correlationId: String,
    val evidenceRefs: List<String> = emptyList(),
    val envelope: CommandResourceEnvelope,
)

enum class EvidenceValidationState { UNVALIDATED, VALID, INVALID, UNKNOWN }

data class EvidenceRecord(
    val evidenceId: String,
    val evidenceType: String,
    val objectRef: String,
    val sourceRef: String,
    val validationState: EvidenceValidationState,
    val integrityHash: String? = null,
    val claimRefs: List<String> = emptyList(),
    val envelope: CommandResourceEnvelope,
)

enum class ReadbackComparison { MATCH, MISMATCH, PARTIAL, UNKNOWN }

data class ReadbackRecord(
    val readbackId: String,
    val objectRef: String,
    val receiptRef: String? = null,
    val comparison: ReadbackComparison,
    val verifierRef: String? = null,
    val envelope: CommandResourceEnvelope,
)

enum class GraphType { INSTITUTIONAL, OPERATIONAL, CAUSAL, EVOLUTIONARY }
enum class GraphRelation { COMPOSES, REQUIRES, GOVERNED_BY, EVIDENCED_BY, CAUSED_BY, PRECEDES, ROUTED_TO, UNKNOWN_EDGE_TYPE }

data class GraphNode(val nodeId: String, val nodeType: String, val label: String, val ocsId: String? = null, val state: String, val sourceRef: String)
data class GraphEdge(val edgeId: String, val fromNodeId: String, val toNodeId: String, val relation: GraphRelation, val sourceRef: String)
data class GraphProjection(val graphId: String, val graphType: GraphType, val nodes: List<GraphNode>, val edges: List<GraphEdge>, val snapshotRef: String, val envelope: CommandResourceEnvelope)

enum class Availability { AVAILABLE, DEGRADED, UNAVAILABLE, UNKNOWN }
enum class Health { HEALTHY, DEGRADED, UNHEALTHY, UNKNOWN }

data class SystemHealthProjection(
    val componentId: String,
    val componentType: String,
    val availability: Availability,
    val health: Health,
    val freshness: Freshness,
    val evidenceRefs: List<String> = emptyList(),
    val envelope: CommandResourceEnvelope,
)

enum class IntentDecision { ACCEPT_FOR_DISPATCH, HOLD, DENY }

data class CommandIntent(
    val intentId: String,
    val organizationId: String,
    val actorRef: String,
    val sourceSurface: String,
    val intentType: String,
    val objectRef: String,
    val requestedAction: String,
    val authorityRef: String? = null,
    val expectedGeneration: Int? = null,
    val expectedSourceVersion: String? = null,
    val idempotencyKey: String,
)

data class CommandIntentDecision(
    val intentId: String,
    val decision: IntentDecision,
    val reason: String,
    val validatedAuthorityRef: String? = null,
    val dispatchRef: String? = null,
    val receiptExpected: Boolean,
    val readbackRequired: Boolean,
)

data class CollectionEnvelope<T>(
    val items: List<T>,
    val cursor: String? = null,
    val nextCursor: String? = null,
    val hasMore: Boolean = false,
    val snapshotRef: String,
    val projectedAt: String,
    val completeness: CompletenessState,
)