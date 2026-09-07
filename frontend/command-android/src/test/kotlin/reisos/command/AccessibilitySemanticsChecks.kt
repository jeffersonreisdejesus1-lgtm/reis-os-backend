package reisos.command

import kotlin.test.Test
import kotlin.test.assertContains
import kotlin.test.assertFalse
import reisos.command.contracts.EpistemicState
import reisos.command.contracts.FreshnessState
import reisos.command.ui.accessibility.commandStateDescription

class AccessibilitySemanticsChecks {
    @Test
    fun syntheticStateDescriptionCarriesNonColorMeaning() {
        val description = commandStateDescription(
            title = "Estado institucional",
            epistemicState = EpistemicState.HOLD,
            freshness = FreshnessState.STALE,
            evidenceLabel = null,
            synthetic = true,
        )

        assertContains(description, "Dados sintéticos")
        assertContains(description, "Estado HOLD")
        assertContains(description, "Atualidade STALE")
        assertContains(description, "Evidência: não comprovada")
        assertFalse(description.contains("healthy", ignoreCase = true))
    }
}
