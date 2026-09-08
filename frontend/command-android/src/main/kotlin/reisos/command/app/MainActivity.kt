package reisos.command

import android.os.Bundle
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.activity.OnBackPressedCallback
import com.google.android.material.divider.MaterialDivider
import reisos.command.app.*

class MainActivity : AppCompatActivity() {
    private lateinit var nav: ProductNavigator
    private lateinit var store: LocalOperationStore

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        store = LocalOperationStore(this)
        nav = ProductNavigator(state?.getString("route") ?: "S0_HOME", state?.getStringArrayList("history").orEmpty())
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() { if (nav.back()) render() else finish() }
        })
        render()
    }

    override fun onSaveInstanceState(out: Bundle) {
        val snapshot = nav.snapshot()
        out.putString("route", snapshot.currentRouteId)
        out.putStringArrayList("history", ArrayList(snapshot.history))
        super.onSaveInstanceState(out)
    }

    private fun go(route: String) {
        if (route == "S2_OPERATION_DETAIL") store.select("CMD-ANDROID-E2E-001")
        if (nav.navigate(route)) render()
    }

    private fun render() {
        val screen = ProductSliceScenario.screen(nav.currentRouteId)
        val records = store.operations()
        val lines = when (screen.routeId) {
            "S0_HOME" -> listOf("persistence=LOCAL_DEVICE", "operations=" + records.size,
                "selected=" + (store.selectedId() ?: "none")) + ProductDataCatalog.homeFacts
            "S1_OPERATIONS" -> records.map { it.id + " · " + it.title + " · " + it.state + " · " + it.progressLabel }
            "S2_OPERATION_DETAIL" -> store.operation(store.selectedId() ?: "CMD-ANDROID-E2E-001")?.let {
                listOf("id=" + it.id, "title=" + it.title, "owner=" + it.owner,
                    "state=" + it.state, "progress=" + it.progressLabel,
                    "lastAction=" + it.lastAction, "revision=" + it.revision,
                    "persistence=SharedPreferences / offline")
            } ?: listOf("operation not found")
            else -> ProductDataCatalog.itemsFor(screen.routeId)
        }
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(20, 20, 20, 20) }
        root.addView(TextView(this).apply { text = "REIS OS Command"; textSize = 26f })
        root.addView(TextView(this).apply { text = "Offline operational slice"; textSize = 13f })
        root.addView(MaterialDivider(this))
        root.addView(TextView(this).apply { text = screen.routeId + " · " + screen.title; textSize = 22f })
        root.addView(TextView(this).apply { text = "STATE: " + screen.semanticState; textSize = 16f })
        root.addView(TextView(this).apply { text = screen.summary; textSize = 16f })
        root.addView(TextView(this).apply { text = lines.joinToString("\n• ", prefix = "\nOperational content\n• "); textSize = 15f })
        if (screen.routeId == "S2_OPERATION_DETAIL") root.addView(Button(this).apply {
            text = "Registrar leitura local"; isAllCaps = false
            setOnClickListener { store.updateAction(store.selectedId() ?: "CMD-ANDROID-E2E-001", "Detalhe consultado localmente"); render() }
        })
        root.addView(TextView(this).apply { text = screen.evidence.joinToString("\n• ", prefix = "\nEvidence / invariants\n• "); textSize = 14f })
        root.addView(TextView(this).apply { text = "Primary navigation"; textSize = 17f })
        ProductSliceScenario.primaryRouteIds().forEach { addButton(root, it) }
        root.addView(TextView(this).apply { text = "All longitudinal surfaces"; textSize = 17f })
        ProductSliceScenario.screens.forEach { addButton(root, it.routeId) }
        root.addView(TextView(this).apply {
            val b = ProductSliceScenario.boundary
            text = "Boundaries\nsource=" + b.sourceClass + "\nliveBackend=" + b.liveBackend +
                "\npostgres=" + b.postgres + "\nrealAtlasL5=" + b.realAtlasL5 +
                "\naiRuntime=" + b.aiRuntime + "\nkernelMutation=" + b.kernelMutation
            textSize = 13f
        })
        setContentView(ScrollView(this).apply { addView(root) })
    }

    private fun addButton(root: LinearLayout, id: String) {
        val target = ProductSliceScenario.screen(id)
        root.addView(Button(this).apply {
            text = target.routeId + " · " + target.title
            isAllCaps = false
            setOnClickListener { go(id) }
        })
    }
}
