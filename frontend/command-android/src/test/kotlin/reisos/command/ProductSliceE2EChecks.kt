package reisos.command

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import reisos.command.app.ProductNavigator
import reisos.command.app.ProductSemanticState
import reisos.command.app.ProductSliceScenario

class ProductSliceE2EChecks {
    @Test
    fun productSliceCoversS0ThroughS9ExactlyOnce() {
        val ids = ProductSliceScenario.screens.map { it.routeId }
        assertEquals(10, ids.size)
        assertEquals(10, ids.toSet().size)
        (0..9).forEach { index -> assertTrue(ids.any { it.startsWith("S${index}_") }) }
    }

    @Test
    fun primaryNavigationRemainsInstitutionalFiveSurfaceSet() {
        assertEquals(
            listOf("S0_HOME", "S1_OPERATIONS", "S3_OCS_DIRECTORY", "S7_EVOLUTION", "S9_CONVERSATION"),
            ProductSliceScenario.primaryRouteIds(),
        )
    }

    @Test
    fun degradedAndEpistemicStatesRemainExplicitAcrossSlice() {
        val states = ProductSliceScenario.screens.map { it.semanticState }.toSet()
        assertTrue(ProductSemanticState.PARTIAL in states)
        assertTrue(ProductSemanticState.STALE in states)
        assertTrue(ProductSemanticState.UNKNOWN in states)
        assertTrue(ProductSemanticState.HOLD in states)
        assertTrue(ProductSemanticState.DENY in states)
        assertTrue(ProductSemanticState.NOT_PROVEN in states)
    }

    @Test
    fun runtimeBoundariesRemainClosed() {
        val b = ProductSliceScenario.boundary
        assertFalse(b.liveBackend)
        assertFalse(b.postgres)
        assertFalse(b.realAtlasL5)
        assertFalse(b.aiRuntime)
        assertFalse(b.kernelMutation)
        assertEquals("LOCAL_PERSISTED_OFFLINE", b.sourceClass)
    }

    @Test
    fun navigationTraversesAllTenSurfacesAndCanRewind() {
        val navigator = ProductNavigator()
        val routeIds = ProductSliceScenario.screens.map { it.routeId }

        routeIds.drop(1).forEach { routeId -> assertTrue(navigator.navigate(routeId)) }
        assertEquals("S9_CONVERSATION", navigator.currentRouteId)
        assertEquals(routeIds.dropLast(1), navigator.snapshot().history)

        repeat(routeIds.size - 1) { assertTrue(navigator.back()) }
        assertEquals("S0_HOME", navigator.currentRouteId)
        assertFalse(navigator.back())
    }

    @Test
    fun navigationSnapshotRestoresCurrentRouteAndHistory() {
        val original = ProductNavigator()
        original.navigate("S1_OPERATIONS")
        original.navigate("S2_OPERATION_DETAIL")
        val snapshot = original.snapshot()

        val restored = ProductNavigator(snapshot.currentRouteId, snapshot.history)
        assertEquals("S2_OPERATION_DETAIL", restored.currentRouteId)
        assertTrue(restored.back())
        assertEquals("S1_OPERATIONS", restored.currentRouteId)
        assertTrue(restored.back())
        assertEquals("S0_HOME", restored.currentRouteId)
    }

    @Test
    fun longitudinalInvariantPackageHasNoFailures() {
        assertEquals(emptyList(), ProductSliceScenario.invariantFailures())
    }

    @Test
    fun everyScreenCarriesEvidenceOrInvariantContext() {
        ProductSliceScenario.screens.forEach { screen ->
            assertTrue(screen.evidence.isNotEmpty(), "${screen.routeId} lacks evidence context")
            assertTrue(screen.summary.isNotBlank(), "${screen.routeId} lacks narrative")
        }
    }
}
