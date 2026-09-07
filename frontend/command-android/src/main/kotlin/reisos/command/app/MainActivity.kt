package reisos.command.app

import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.divider.MaterialDivider
import reisos.command.BuildConfig

class MainActivity : AppCompatActivity() {
    companion object {
        private const val STATE_ROUTE = "command.route"
        private const val STATE_HISTORY = "command.history"
    }

    private lateinit var navigator: ProductNavigator

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        navigator = ProductNavigator(
            startRouteId = savedInstanceState?.getString(STATE_ROUTE) ?: "S0_HOME",
            priorHistory = savedInstanceState?.getStringArrayList(STATE_HISTORY).orEmpty(),
        )

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (navigator.back()) {
                    render()
                } else {
                    finish()
                }
            }
        })
        render()
    }

    override fun onSaveInstanceState(outState: Bundle) {
        val snapshot = navigator.snapshot()
        outState.putString(STATE_ROUTE, snapshot.currentRouteId)
        outState.putStringArrayList(STATE_HISTORY, ArrayList(snapshot.history))
        super.onSaveInstanceState(outState)
    }

    private fun navigate(routeId: String) {
        if (navigator.navigate(routeId)) render()
    }

    private fun render() {
        val spec = ProductSliceScenario.screen(navigator.currentRouteId)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(20), dp(20), dp(20))
        }

        root.addView(TextView(this).apply {
            text = "REIS OS Command"
            textSize = 26f
            setTextIsSelectable(true)
            contentDescription = "REIS OS Command"
        })

        root.addView(TextView(this).apply {
            text = "Synthetic longitudinal product slice • ${BuildConfig.VERSION_NAME}"
            textSize = 13f
            contentDescription = "Synthetic longitudinal product slice version ${BuildConfig.VERSION_NAME}"
        })

        root.addView(MaterialDivider(this))

        root.addView(TextView(this).apply {
            text = spec.title
            textSize = 22f
            setPadding(0, dp(18), 0, dp(6))
            contentDescription = "Screen ${spec.routeId}: ${spec.title}"
        })

        root.addView(TextView(this).apply {
            text = "STATE: ${spec.semanticState}"
            textSize = 16f
            setPadding(0, 0, 0, dp(10))
            contentDescription = "Semantic state ${spec.semanticState}"
        })

        root.addView(TextView(this).apply {
            text = spec.summary
            textSize = 16f
            setTextIsSelectable(true)
        })

        root.addView(TextView(this).apply {
            text = spec.evidence.joinToString(prefix = "\nEvidence / invariants\n• ", separator = "\n• ")
            textSize = 14f
            setTextIsSelectable(true)
            importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_YES
        })

        root.addView(MaterialDivider(this).apply { setPadding(0, dp(18), 0, dp(8)) })

        root.addView(TextView(this).apply {
            text = "Primary navigation"
            textSize = 17f
            contentDescription = "Primary navigation"
        })

        ProductSliceScenario.primaryRouteIds().forEach { routeId -> addRouteButton(root, routeId) }

        root.addView(TextView(this).apply {
            text = "All longitudinal surfaces"
            textSize = 17f
            setPadding(0, dp(14), 0, dp(4))
            contentDescription = "All longitudinal surfaces"
        })

        ProductSliceScenario.screens.forEach { screen -> addRouteButton(root, screen.routeId) }

        root.addView(MaterialDivider(this).apply { setPadding(0, dp(18), 0, dp(8)) })

        root.addView(TextView(this).apply {
            val b = ProductSliceScenario.boundary
            text = buildString {
                append("Boundaries\n")
                append("source=${b.sourceClass}\n")
                append("liveBackend=${b.liveBackend}\n")
                append("postgres=${b.postgres}\n")
                append("realAtlasL5=${b.realAtlasL5}\n")
                append("aiRuntime=${b.aiRuntime}\n")
                append("kernelMutation=${b.kernelMutation}")
            }
            textSize = 13f
            setTextIsSelectable(true)
        })

        val scroll = ScrollView(this).apply {
            isFillViewport = true
            addView(root)
        }

        setContentView(scroll)
    }

    private fun addRouteButton(root: LinearLayout, routeId: String) {
        val target = ProductSliceScenario.screen(routeId)
        root.addView(Button(this).apply {
            text = "${target.routeId} · ${target.title}"
            contentDescription = "Open ${target.title}"
            minHeight = dp(48)
            isAllCaps = false
            setOnClickListener { navigate(routeId) }
        })
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}
