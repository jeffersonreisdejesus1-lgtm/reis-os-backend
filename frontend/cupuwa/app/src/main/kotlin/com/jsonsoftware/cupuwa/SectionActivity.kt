package com.jsonsoftware.cupuwa

import android.os.Bundle
import android.widget.TextView
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Toast
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.MaterialAutoCompleteTextView
import com.google.android.material.textfield.TextInputEditText
import androidx.appcompat.app.AppCompatActivity

class SectionActivity : AppCompatActivity() {
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        setContentView(R.layout.activity_section)
        val section = intent.getStringExtra(EXTRA_SECTION) ?: PLAN
        val planning = section == PLAN
        val insights = section == INSIGHTS
        findViewById<TextView>(R.id.sectionTitle).text = when { planning -> getString(R.string.section_plan); insights -> "Insights"; else -> getString(R.string.section_settings) }
        findViewById<TextView>(R.id.sectionBody).text = when { planning -> getString(R.string.section_plan_body); insights -> "Ainda precisamos de mais movimentos para gerar insights."; else -> getString(R.string.section_settings_body) }
        findViewById<View>(R.id.planningForm).visibility = if (planning) View.VISIBLE else View.GONE
        findViewById<View>(R.id.insightsEmpty).visibility = if (insights) View.VISIBLE else View.GONE
        findViewById<View>(R.id.settingsForm).visibility = if (planning || insights) View.GONE else View.VISIBLE
        findViewById<MaterialButton>(R.id.navHome).setOnClickListener {
            startActivity(android.content.Intent(this, MainActivity::class.java).apply {
                addFlags(android.content.Intent.FLAG_ACTIVITY_CLEAR_TOP or android.content.Intent.FLAG_ACTIVITY_SINGLE_TOP)
            })
        }
        findViewById<MaterialButton>(R.id.navMovements).setOnClickListener { startActivity(android.content.Intent(this, MovementActivity::class.java)) }
        findViewById<MaterialButton>(R.id.navPlan).setOnClickListener { startActivity(intent.putExtra(EXTRA_SECTION, PLAN)) }
        findViewById<MaterialButton>(R.id.navInsights).setOnClickListener { startActivity(intent.putExtra(EXTRA_SECTION, INSIGHTS)) }
        findViewById<MaterialButton>(R.id.navSettings).setOnClickListener { startActivity(intent.putExtra(EXTRA_SECTION, SETTINGS)) }
        val activeId = when { planning -> R.id.navPlan; insights -> R.id.navInsights; else -> R.id.navSettings }
        findViewById<MaterialButton>(activeId).setTextColor(getColor(R.color.cupuwa_accent))
        findViewById<MaterialButton>(R.id.backButton).setOnClickListener { finish() }
        val store = ProductStore(this)
        if (planning) {
            val categories = store.categories().filter { it.kind == MoneyEntry.Kind.EXPENSE }
            findViewById<MaterialAutoCompleteTextView>(R.id.planCategory).apply { setAdapter(ArrayAdapter(context, android.R.layout.simple_dropdown_item_1line, categories.map { it.name })); setText(categories.firstOrNull()?.name, false) }
            fun refresh() { findViewById<TextView>(R.id.planningSummary).text = ProductMath.budgetProgress(store.budgets(), store.categories(), LocalLedgerStore(this).entries()).joinToString("\n") { "${it.category?.name ?: "Categoria"}: ${it.percent}% usado · resta ${LedgerMath.formatBrl(it.remainingCents)}" }.ifBlank { "Nenhum orçamento criado ainda." } }
            refresh()
            findViewById<MaterialButton>(R.id.saveBudget).setOnClickListener { runCatching { val name=findViewById<MaterialAutoCompleteTextView>(R.id.planCategory).text.toString(); val id=categories.first { it.name == name }.id; val limit=LedgerMath.parseCents(findViewById<TextInputEditText>(R.id.planLimit).text.toString()); store.saveBudget(id, limit); refresh(); findViewById<TextInputEditText>(R.id.planLimit).text?.clear() }.onFailure { Toast.makeText(this, it.message ?: "Não foi possível criar", Toast.LENGTH_SHORT).show() } }
        } else {
            findViewById<TextInputEditText>(R.id.profileName).setText(store.profile().name)
            findViewById<MaterialButton>(R.id.saveProfile).setOnClickListener { val name=findViewById<TextInputEditText>(R.id.profileName).text.toString().trim(); store.saveProfile(store.profile().copy(name=name, onboardingComplete=name.isNotBlank())); Toast.makeText(this, "Perfil salvo", Toast.LENGTH_SHORT).show() }
            findViewById<MaterialButton>(R.id.clearData).setOnClickListener { store.clearAll(); LocalLedgerStore(this).clear(); Toast.makeText(this, "Dados locais apagados", Toast.LENGTH_SHORT).show() }
        }
    }
    companion object { const val EXTRA_SECTION = "section"; const val PLAN = "plan"; const val SETTINGS = "settings"; const val INSIGHTS = "insights" }
}
