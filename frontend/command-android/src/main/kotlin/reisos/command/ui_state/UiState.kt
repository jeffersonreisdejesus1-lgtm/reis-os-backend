package reisos.command.ui_state

import reisos.command.contracts.CompletenessState
import reisos.command.contracts.FreshnessState

sealed interface UiState<out T> {
    data object Initial : UiState<Nothing>
    data object Loading : UiState<Nothing>
    data class Content<T>(val value: T, val freshness: FreshnessState, val completeness: CompletenessState) : UiState<T>
    data object Empty : UiState<Nothing>
    data class Partial<T>(val value: T, val missingFields: List<String>) : UiState<T>
    data class Stale<T>(val value: T, val reason: String? = null) : UiState<T>
    data class Unknown(val reason: String? = null) : UiState<Nothing>
    data class Error(val message: String, val retryable: Boolean) : UiState<Nothing>
    data class Denied(val reason: String) : UiState<Nothing>
    data class Hold(val reason: String) : UiState<Nothing>
}

/**
 * Safe collection mapping. UNKNOWN never becomes EMPTY; PARTIAL never becomes COMPLETE.
 */
fun <T> mapCollectionState(
    items: List<T>,
    completeness: CompletenessState,
    freshness: FreshnessState,
    missingFields: List<String> = emptyList(),
): UiState<List<T>> = when {
    completeness == CompletenessState.UNKNOWN -> UiState.Unknown("collection completeness unknown")
    completeness == CompletenessState.PARTIAL -> UiState.Partial(items, missingFields)
    items.isEmpty() && completeness == CompletenessState.COMPLETE -> UiState.Empty
    freshness == FreshnessState.STALE -> UiState.Stale(items, "collection freshness stale")
    freshness == FreshnessState.UNKNOWN -> UiState.Unknown("collection freshness unknown")
    else -> UiState.Content(items, freshness, completeness)
}