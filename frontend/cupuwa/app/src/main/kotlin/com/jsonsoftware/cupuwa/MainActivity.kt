package com.jsonsoftware.cupuwa

import android.graphics.Color
import android.os.Bundle
import android.text.InputType
import android.view.ViewGroup
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.button.MaterialButton

class MainActivity : AppCompatActivity() {
    private lateinit var store: LocalLedgerStore
    private lateinit var balanceView: TextView
    private lateinit var amountInput: EditText
    private lateinit var descriptionInput: EditText
    private lateinit var historyView: LinearLayout
    private lateinit var primaryAction: MaterialButton
    private var editingId: Long? = null
    private var editingKind: MoneyEntry.Kind = MoneyEntry.Kind.INCOME

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        store = LocalLedgerStore(this)
        render()
    }

    private fun render() {
        val padding = dp(20)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding, padding, padding, padding)
        }

        root.addView(TextView(this).apply {
            text = "CUPUWA"
            textSize = 30f
            setTextColor(Color.rgb(42, 28, 72))
            contentDescription = "CUPUWA"
        })
        root.addView(TextView(this).apply {
            text = "Seu dinheiro, claro e local."
            textSize = 16f
        })

        root.addView(label("Saldo atual", padding))
        balanceView = TextView(this).apply {
            textSize = 36f
            setTextColor(Color.rgb(42, 28, 72))
            contentDescription = "Saldo atual"
        }
        root.addView(balanceView)

        root.addView(label("Valor", padding))
        amountInput = EditText(this).apply {
            hint = "Ex.: 25,90"
            inputType = InputType.TYPE_CLASS_TEXT
            contentDescription = "Valor da movimentação"
        }
        root.addView(amountInput, fieldParams())

        root.addView(label("Descrição", 4))
        descriptionInput = EditText(this).apply {
            hint = "Opcional"
            contentDescription = "Descrição da movimentação"
        }
        root.addView(descriptionInput, fieldParams())

        val actions = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, 8, 0, 0)
        }
        primaryAction = MaterialButton(this).apply {
            text = "Adicionar entrada"
            isAllCaps = false
            minHeight = dp(48)
            contentDescription = "Adicionar entrada"
            setOnClickListener { record(MoneyEntry.Kind.INCOME) }
        }
        actions.addView(primaryAction)
        actions.addView(MaterialButton(this).apply {
            text = "Adicionar saída"
            isAllCaps = false
            minHeight = dp(48)
            contentDescription = "Adicionar saída"
            setOnClickListener { record(MoneyEntry.Kind.EXPENSE) }
        })
        actions.addView(MaterialButton(this).apply {
            text = "Cancelar edição"
            isAllCaps = false
            minHeight = dp(48)
            contentDescription = "Cancelar edição"
            setOnClickListener { clearEditor() }
        })
        root.addView(actions)

        root.addView(TextView(this).apply {
            text = "Histórico"
            textSize = 22f
            setPadding(0, padding, 0, padding / 2)
            contentDescription = "Histórico"
        })
        historyView = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        root.addView(historyView)

        setContentView(ScrollView(this).apply { addView(root) })
        refresh()
    }

    private fun record(kind: MoneyEntry.Kind) {
        runCatching {
            val cents = LedgerMath.parseCents(amountInput.text.toString())
            val description = descriptionInput.text.toString()
            val currentId = editingId
            if (currentId == null) {
                store.add(cents, kind, description)
            } else {
                store.update(currentId, cents, kind, description)
            }
            clearEditor()
            refresh()
        }.onFailure {
            Toast.makeText(this, it.message ?: "Valor inválido", Toast.LENGTH_SHORT).show()
        }
    }

    private fun refresh() {
        val entries = store.entries()
        balanceView.text = LedgerMath.formatBrl(LedgerMath.balanceCents(entries))
        historyView.removeAllViews()
        if (entries.isEmpty()) {
            historyView.addView(TextView(this).apply {
                text = "Nenhuma movimentação ainda."
                textSize = 16f
                setPadding(0, 8, 0, 8)
                contentDescription = "Nenhuma movimentação ainda"
            })
            return
        }
        entries.forEach { entry ->
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(0, 8, 0, 8)
            }
            val kindLabel = if (entry.kind == MoneyEntry.Kind.INCOME) "entrada" else "saída"
            val sign = if (entry.kind == MoneyEntry.Kind.INCOME) "+" else "-"
            row.addView(TextView(this).apply {
                text = "$sign ${LedgerMath.formatBrl(entry.cents)} · ${entry.description} ($kindLabel)"
                textSize = 16f
                contentDescription = text
            })
            val buttons = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
            buttons.addView(MaterialButton(this).apply {
                text = "Editar"
                isAllCaps = false
                contentDescription = "Editar ${entry.description}"
                setOnClickListener { startEdit(entry) }
            })
            buttons.addView(MaterialButton(this).apply {
                text = "Excluir"
                isAllCaps = false
                contentDescription = "Excluir ${entry.description}"
                setOnClickListener { confirmDelete(entry) }
            })
            row.addView(buttons)
            historyView.addView(row)
        }
    }

    private fun startEdit(entry: MoneyEntry) {
        editingId = entry.id
        editingKind = entry.kind
        amountInput.setText(LedgerMath.formatBrl(entry.cents).removePrefix("- ").removePrefix("R$ "))
        descriptionInput.setText(entry.description)
        primaryAction.text = "Salvar alteração"
        primaryAction.contentDescription = "Salvar alteração"
        primaryAction.setOnClickListener { record(editingKind) }
        Toast.makeText(this, "Editando lançamento", Toast.LENGTH_SHORT).show()
    }

    private fun confirmDelete(entry: MoneyEntry) {
        AlertDialog.Builder(this)
            .setTitle("Excluir lançamento?")
            .setMessage("${LedgerMath.formatBrl(entry.cents)} · ${entry.description}")
            .setNegativeButton("Cancelar", null)
            .setPositiveButton("Excluir") { _, _ ->
                store.delete(entry.id)
                if (editingId == entry.id) clearEditor()
                refresh()
            }
            .show()
    }

    private fun clearEditor() {
        editingId = null
        amountInput.text.clear()
        descriptionInput.text.clear()
        primaryAction.text = "Adicionar entrada"
        primaryAction.contentDescription = "Adicionar entrada"
        primaryAction.setOnClickListener { record(MoneyEntry.Kind.INCOME) }
    }

    private fun label(text: String, top: Int) = TextView(this).apply {
        this.text = text
        textSize = 17f
        setPadding(0, top, 0, 4)
    }

    private fun fieldParams() = LinearLayout.LayoutParams(
        ViewGroup.LayoutParams.MATCH_PARENT,
        ViewGroup.LayoutParams.WRAP_CONTENT,
    ).apply { bottomMargin = 8 }

    private fun dp(value: Int): Int =
        (value * resources.displayMetrics.density).toInt()
}
