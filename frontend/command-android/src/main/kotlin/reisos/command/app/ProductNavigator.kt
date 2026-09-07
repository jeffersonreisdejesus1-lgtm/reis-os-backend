package reisos.command.app

import java.util.ArrayDeque

data class NavigationSnapshot(
    val currentRouteId: String,
    val history: List<String>,
)

class ProductNavigator(
    startRouteId: String = "S0_HOME",
    priorHistory: List<String> = emptyList(),
) {
    private val history = ArrayDeque<String>().apply { priorHistory.forEach(::addLast) }

    var currentRouteId: String = startRouteId
        private set

    fun navigate(routeId: String): Boolean {
        if (routeId == currentRouteId) return false
        require(ProductSliceScenario.screens.any { it.routeId == routeId }) { "Unknown Command route: $routeId" }
        history.addLast(currentRouteId)
        currentRouteId = routeId
        return true
    }

    fun back(): Boolean {
        if (history.isEmpty()) return false
        currentRouteId = history.removeLast()
        return true
    }

    fun snapshot(): NavigationSnapshot = NavigationSnapshot(
        currentRouteId = currentRouteId,
        history = history.toList(),
    )
}
