package reisos.command.app

data class JourneyStep(
    val routeId: String,
    val purpose: String,
    val expectedState: ProductSemanticState,
    val nextRouteId: String?,
)

object ProductJourney {
    val founderObservationPath: List<JourneyStep> = listOf(
        JourneyStep("S0_HOME", "Detect institutional attention", ProductSemanticState.NOT_PROVEN, "S1_OPERATIONS"),
        JourneyStep("S1_OPERATIONS", "Select operation with unknown progress", ProductSemanticState.UNKNOWN, "S2_OPERATION_DETAIL"),
        JourneyStep("S2_OPERATION_DETAIL", "Inspect receipt/readback gap", ProductSemanticState.NOT_PROVEN, "S6_EVIDENCE"),
        JourneyStep("S6_EVIDENCE", "Inspect evidence validity", ProductSemanticState.NOT_PROVEN, "S5_MAPS"),
        JourneyStep("S5_MAPS", "Inspect causal projection under HOLD", ProductSemanticState.HOLD, "S8_SYSTEM"),
        JourneyStep("S8_SYSTEM", "Inspect stale system state", ProductSemanticState.STALE, "S0_HOME"),
    )

    val ocsInspectionPath: List<JourneyStep> = listOf(
        JourneyStep("S0_HOME", "Open institutional situation", ProductSemanticState.NOT_PROVEN, "S3_OCS_DIRECTORY"),
        JourneyStep("S3_OCS_DIRECTORY", "Inspect ten-OCS roster", ProductSemanticState.CURRENT, "S4_OCS_DETAIL"),
        JourneyStep("S4_OCS_DETAIL", "Inspect partial instance binding", ProductSemanticState.PARTIAL, "S6_EVIDENCE"),
        JourneyStep("S6_EVIDENCE", "Require evidence before stronger claim", ProductSemanticState.NOT_PROVEN, "S0_HOME"),
    )

    fun validate(path: List<JourneyStep>): List<String> = buildList {
        if (path.isEmpty()) add("journey_empty")
        path.forEachIndexed { index, step ->
            val screen = ProductSliceScenario.screen(step.routeId)
            if (screen.routeId != step.routeId) add("unknown_route:${step.routeId}")
            if (screen.semanticState != step.expectedState) {
                add("state_mismatch:${step.routeId}:${screen.semanticState}:${step.expectedState}")
            }
            val next = path.getOrNull(index + 1)?.routeId ?: path.firstOrNull()?.routeId
            if (step.nextRouteId != next) add("next_route_mismatch:${step.routeId}:${step.nextRouteId}:$next")
        }
    }
}
