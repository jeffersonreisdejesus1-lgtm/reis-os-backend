package reisos.command

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import reisos.command.app.ProductSemanticState
import reisos.command.app.ProductSliceScenario

class ProductSliceE2EChecks {
    @Test
    fun productSliceCoversS0ThroughS9ExactlyOnce() {
        val ids = ProductSliceScenario.screens.map { it.routeId }
        assertEquals((0..9).map { "S${it}_" }.size, ids.size)
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
        assertEquals("SYNTHETIC_UI_FIXTURE", b.sourceClass)
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
