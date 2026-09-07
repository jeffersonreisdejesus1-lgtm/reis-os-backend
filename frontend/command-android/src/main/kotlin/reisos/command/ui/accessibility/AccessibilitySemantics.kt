package reisos.command.ui.accessibility

import reisos.command.contracts.EpistemicState
import reisos.command.contracts.FreshnessState

/** Pure semantic formatter so accessibility meaning is testable without a device. */
fun commandStateDescription(
    title: String,
    epistemicState: EpistemicState,
    freshness: FreshnessState,
    evidenceLabel: String?,
    synthetic: Boolean,
): String = buildString {
    if (synthetic) append("Dados sintéticos. ")
    append(title)
    append(". Estado ")
    append(epistemicState.name)
    append(". Atualidade ")
    append(freshness.name)
    append(". Evidência: ")
    append(evidenceLabel ?: "não comprovada")
}
