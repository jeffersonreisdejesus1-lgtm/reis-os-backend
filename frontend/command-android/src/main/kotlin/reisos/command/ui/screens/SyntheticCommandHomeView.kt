package reisos.command.ui.screens

import android.content.Context
import android.util.AttributeSet
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import reisos.command.contracts.EpistemicState
import reisos.command.contracts.FreshnessState
import reisos.command.ui.components.CommandStatePanel
import reisos.command.ui.components.StatePanelModel

/**
 * S0 Android presentation surface using synthetic fixture-shaped values only.
 * No transport, repository, Kernel, Atlas, Postgres, L5 or AI dependency exists here.
 */
class SyntheticCommandHomeView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : LinearLayout(context, attrs) {

    init {
        orientation = VERTICAL
        setPadding(dp(16), dp(16), dp(16), dp(16))
        importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_YES

        addView(sectionTitle("REIS OS Command — cenário sintético"))
        addView(
            CommandStatePanel(context).apply {
                bind(
                    StatePanelModel(
                        title = "Estado institucional",
                        epistemicState = EpistemicState.NOT_PROVEN,
                        freshness = FreshnessState.UNKNOWN,
                        evidenceLabel = null,
                        synthetic = true,
                    )
                )
            }
        )
        addView(
            CommandStatePanel(context).apply {
                bind(
                    StatePanelModel(
                        title = "Atenção do Founder",
                        epistemicState = EpistemicState.HOLD,
                        freshness = FreshnessState.STALE,
                        evidenceLabel = "fixture:evidence-founder-attention",
                        synthetic = true,
                    )
                )
            }
        )
        addView(
            CommandStatePanel(context).apply {
                bind(
                    StatePanelModel(
                        title = "Sistema",
                        epistemicState = EpistemicState.UNKNOWN,
                        freshness = FreshnessState.UNKNOWN,
                        evidenceLabel = null,
                        synthetic = true,
                    )
                )
            }
        )
    }

    private fun sectionTitle(text: String): TextView = TextView(context).apply {
        this.text = text
        textSize = 20f
        setPadding(0, 0, 0, dp(12))
        contentDescription = "$text. Não representa estado institucional real."
    }

    private fun dp(value: Int): Int =
        (value * resources.displayMetrics.density).toInt()
}
