package reisos.command.ui.components

import android.content.Context
import android.graphics.Typeface
import android.util.AttributeSet
import android.view.Gravity
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import reisos.command.contracts.EpistemicState
import reisos.command.contracts.FreshnessState

/**
 * Real Android View component for synthetic-only Command UI rehearsal.
 *
 * It never creates authority, dispatches intents, or writes canonical state.
 * State meaning is carried by text + shape/layout semantics; color is optional.
 */
class CommandStatePanel @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : LinearLayout(context, attrs) {

    private val titleView = TextView(context)
    private val stateView = TextView(context)
    private val freshnessView = TextView(context)
    private val evidenceView = TextView(context)

    init {
        orientation = VERTICAL
        gravity = Gravity.START
        minimumHeight = dp(48)
        setPadding(dp(16), dp(12), dp(16), dp(12))
        isImportantForAccessibility = true
        importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_YES

        titleView.setTypeface(titleView.typeface, Typeface.BOLD)
        addView(titleView, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        addView(stateView, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        addView(freshnessView, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        addView(evidenceView, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
    }

    fun bind(model: StatePanelModel) {
        titleView.text = model.title
        stateView.text = "Estado: ${model.epistemicState.name}"
        freshnessView.text = "Atualidade: ${model.freshness.name}"
        evidenceView.text = when {
            model.evidenceLabel != null -> "Evidência: ${model.evidenceLabel}"
            else -> "Evidência: não comprovada"
        }

        val syntheticMarker = if (model.synthetic) "Dados sintéticos. " else ""
        contentDescription = buildString {
            append(syntheticMarker)
            append(model.title)
            append(". Estado ")
            append(model.epistemicState.name)
            append(". Atualidade ")
            append(model.freshness.name)
            append(". ")
            append(evidenceView.text)
        }
    }

    private fun dp(value: Int): Int =
        (value * resources.displayMetrics.density).toInt()
}

data class StatePanelModel(
    val title: String,
    val epistemicState: EpistemicState,
    val freshness: FreshnessState,
    val evidenceLabel: String? = null,
    val synthetic: Boolean,
)
