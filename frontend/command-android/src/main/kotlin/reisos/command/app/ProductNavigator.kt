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
    private val history = ArrayDeque<String>().apply {
        priorHistory.forEach { addLast(it) }
    }

    var currentRouteId: String = startRouteId
        private set

    init {
        require(ProductSliceScenario.screens.any { it.routeId == currentRouteId }) {
            "Unknown Command start route: $currentRouteId"
        }
        require(priorHistory.all { prior -> ProductSliceScenario.screens.any { it.routeId == prior } }) {
            "Unknown Command route in navigation history"
        }
    }

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
