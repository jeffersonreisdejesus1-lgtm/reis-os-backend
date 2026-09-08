package reisos.command

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import reisos.command.app.ProductDataCatalog
import reisos.command.app.ProductSemanticState
import reisos.command.app.ProductSliceScenario

class ProductDataCatalogChecks {
    @Test
    fun tenOcsRosterIsCompleteAndUnique() {
        val roster = ProductDataCatalog.ocsRoster
        assertEquals(10, roster.size)
        assertEquals(10, roster.map { it.id }.toSet().size)
        assertEquals(10, roster.map { it.name }.toSet().size)
    }

    @Test
    fun canonicalOcsRosterNamesRemainStableInsideSyntheticSlice() {
        assertEquals(
            setOf("NÓESIS", "DÉDALA", "SÝNESIS", "ÍRIS", "LYRA", "SOFIA", "MÊTIS", "ÁGORA", "AURI", "SYNERGEIA"),
            ProductDataCatalog.ocsRoster.map { it.name }.toSet(),
        )
    }

    @Test
    fun everyLongitudinalSurfaceHasOperationalContent() {
        ProductSliceScenario.screens.forEach { screen ->
            assertTrue(
                ProductDataCatalog.itemsFor(screen.routeId).isNotEmpty(),
                "${screen.routeId} has no operational content",
            )
        }
    }

    @Test
    fun operationsNeverFabricateMeasuredProgress() {
        assertTrue(ProductDataCatalog.operations.any { it.state == ProductSemanticState.UNKNOWN })
        assertTrue(ProductDataCatalog.operations.any { it.progressLabel.startsWith("UNKNOWN") })
        assertFalse(ProductDataCatalog.operations.any { it.progressLabel.contains("100%") })
    }

    @Test
    fun atlasAndEvidenceUncertaintyRemainHeldOrNotProven() {
        assertTrue(ProductDataCatalog.systems.any { it.id == "ATLAS" && it.freshness == ProductSemanticState.HOLD })
        assertTrue(ProductDataCatalog.evidence.any { it.state == ProductSemanticState.HOLD })
        assertTrue(ProductDataCatalog.evidence.any { it.state == ProductSemanticState.NOT_PROVEN })
    }

    @Test
    fun homeFactsNeverClaimRuntimeMutation() {
        assertTrue(ProductDataCatalog.homeFacts.any { it.contains("0 caminhos de mutação do Kernel") })
    }

    @Test
    fun systemCatalogSeparatesAvailabilityFromFreshness() {
        val command = ProductDataCatalog.systems.single { it.id == "COMMAND" }
        assertEquals("AVAILABLE", command.availability)
        assertEquals(ProductSemanticState.STALE, command.freshness)
    }

    @Test
    fun evidenceCatalogDoesNotContainAssuredClaims() {
        assertFalse(ProductDataCatalog.evidence.any { it.validation == "ASSURED" })
    }
}
