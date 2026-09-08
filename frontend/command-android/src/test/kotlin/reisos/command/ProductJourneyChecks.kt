package reisos.command

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import reisos.command.app.ProductJourney

class ProductJourneyChecks {
    @Test
    fun founderObservationJourneyIsInternallyCoherent() {
        assertEquals(emptyList(), ProductJourney.validate(ProductJourney.founderObservationPath))
        assertEquals("S0_HOME", ProductJourney.founderObservationPath.first().routeId)
        assertEquals("S8_SYSTEM", ProductJourney.founderObservationPath.last().routeId)
    }

    @Test
    fun ocsInspectionJourneyIsInternallyCoherent() {
        assertEquals(emptyList(), ProductJourney.validate(ProductJourney.ocsInspectionPath))
        assertEquals("S0_HOME", ProductJourney.ocsInspectionPath.first().routeId)
        assertEquals("S6_EVIDENCE", ProductJourney.ocsInspectionPath.last().routeId)
    }

    @Test
    fun journeysCrossEvidenceBeforeReturningHome() {
        assertTrue(ProductJourney.founderObservationPath.any { it.routeId == "S6_EVIDENCE" })
        assertTrue(ProductJourney.ocsInspectionPath.any { it.routeId == "S6_EVIDENCE" })
    }
}
