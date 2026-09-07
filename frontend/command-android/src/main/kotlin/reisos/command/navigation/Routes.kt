package reisos.command.navigation

sealed class CommandRoute(val id: String) {
    data object Home : CommandRoute("S0_HOME")
    data object Operations : CommandRoute("S1_OPERATIONS")
    data class OperationDetail(val operationId: String) : CommandRoute("S2_OPERATION_DETAIL")
    data object OcsDirectory : CommandRoute("S3_OCS_DIRECTORY")
    data class OcsDetail(val ocsId: String) : CommandRoute("S4_OCS_DETAIL")
    data class Maps(val graphId: String? = null) : CommandRoute("S5_MAPS")
    data object Evidence : CommandRoute("S6_EVIDENCE")
    data object Evolution : CommandRoute("S7_EVOLUTION")
    data object System : CommandRoute("S8_SYSTEM")
    data object Conversation : CommandRoute("S9_CONVERSATION")
}

val primaryNavigation = listOf(
    CommandRoute.Home,
    CommandRoute.Operations,
    CommandRoute.OcsDirectory,
    CommandRoute.Evolution,
    CommandRoute.Conversation,
)

/** Navigation context never grants authority. */
data class NavigationContext(
    val objectRef: String? = null,
    val contextRefs: List<String> = emptyList(),
)