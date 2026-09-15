package com.jsonsoftware.cupuwa

import android.os.Bundle
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText

class MovementActivity : AppCompatActivity() {
    private lateinit var store: LocalLedgerStore
    private var editingId: Long = -1L
    private lateinit var kind: MoneyEntry.Kind

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        setContentView(R.layout.activity_movement)
        findViewById<MaterialButton>(R.id.navHome).setOnClickListener { finish() }
        findViewById<MaterialButton>(R.id.navMovements).setOnClickListener { }
        findViewById<MaterialButton>(R.id.navPlan).setOnClickListener { startActivity(android.content.Intent(this, SectionActivity::class.java).putExtra(SectionActivity.EXTRA_SECTION, SectionActivity.PLAN)) }
        findViewById<MaterialButton>(R.id.navInsights).setOnClickListener { startActivity(android.content.Intent(this, SectionActivity::class.java).putExtra(SectionActivity.EXTRA_SECTION, SectionActivity.INSIGHTS)) }
        findViewById<MaterialButton>(R.id.navSettings).setOnClickListener { startActivity(android.content.Intent(this, SectionActivity::class.java).putExtra(SectionActivity.EXTRA_SECTION, SectionActivity.SETTINGS)) }
        store = LocalLedgerStore(this)
        kind = MoneyEntry.Kind.valueOf(
            intent.getStringExtra(EXTRA_KIND) ?: MoneyEntry.Kind.INCOME.name,
        )
        editingId = intent.getLongExtra(EXTRA_ID, -1L)
        val title = findViewById<TextView>(R.id.movementTitle)
        val amount = findViewById<TextInputEditText>(R.id.amountInput)
        val description = findViewById<TextInputEditText>(R.id.descriptionInput)
        if (editingId > 0) {
            val current = store.get(editingId)
            if (current != null) {
                kind = current.kind
                amount.setText(LedgerMath.formatBrl(current.cents).removePrefix("- ").removePrefix("R$ ").trim())
                description.setText(current.description)
                title.text = "Editar ${if (kind == MoneyEntry.Kind.INCOME) "entrada" else "saída"}"
            } else {
                title.text = "Lançamento"
            }
        } else {
            title.text = if (kind == MoneyEntry.Kind.INCOME) "Nova entrada" else "Nova saída"
        }
        findViewById<MaterialButton>(R.id.saveButton).setOnClickListener {
            runCatching {
                val cents = LedgerMath.parseCents(amount.text?.toString().orEmpty())
                val note = description.text?.toString().orEmpty()
                if (editingId > 0) store.update(editingId, cents, kind, note)
                else store.add(cents, kind, note)
                finish()
            }.onFailure {
                Toast.makeText(this, it.message ?: "Valor inválido", Toast.LENGTH_SHORT).show()
            }
        }
    }

    companion object {
        const val EXTRA_KIND = "kind"
        const val EXTRA_ID = "id"
    }
}
