package com.jsonsoftware.cupuwa

import android.graphics.Color
import android.os.Bundle
import android.text.InputType
import android.view.ViewGroup
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.button.MaterialButton

class MainActivity : AppCompatActivity() {
    private lateinit var store: LocalLedgerStore
    private lateinit var balanceView: TextView
    private lateinit var amountInput: EditText
    private lateinit var descriptionInput: EditText
    private lateinit var historyView: LinearLayout

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        store = LocalLedgerStore(this)
        render()
    }

    private fun render() {
        val padding = (20 * resources.displayMetrics.density).toInt()
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding, padding, padding, padding)
        }

        root.addView(TextView(this).apply {
            text = "CUPUWA"
            textSize = 30f
            setTextColor(Color.rgb(42, 28, 72))
        })
        root.addView(TextView(this).apply {
            text = "Seu dinheiro, claro e local."
            textSize = 16f
        })
        balanceView = TextView(this).apply {
            textSize = 34f
            setTextColor(Color.rgb(42, 28, 72))
        }
        root.addView(balanceView)

        amountInput = EditText(this).apply {
            hint = "Valor (ex.: 25,90)"
            inputType = InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_FLAG_DECIMAL
        }
        root.addView(amountInput, fieldParams())

        descriptionInput = EditText(this).apply {
            hint = "Descrição (opcional)"
        }
        root.addView(descriptionInput, fieldParams())

        val actions = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        actions.addView(MaterialButton(this).apply {
            text = "Entrou"
            setOnClickListener { record(MoneyEntry.Kind.INCOME) }
        }, weightParams())
        actions.addView(MaterialButton(this).apply {
            text = "Saiu"
            setOnClickListener { record(MoneyEntry.Kind.EXPENSE) }
        }, weightParams())
        root.addView(actions)

        root.addView(TextView(this).apply {
            text = "Histórico"
            textSize = 22f
            setPadding(0, padding, 0, padding / 2)
        })
        historyView = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        root.addView(historyView)

        setContentView(ScrollView(this).apply { addView(root) })
        refresh()
    }

    private fun record(kind: MoneyEntry.Kind) {
        runCatching {
            val cents = LedgerMath.parseCents(amountInput.text.toString())
            store.add(cents, kind, descriptionInput.text.toString())
            amountInput.text.clear()
            descriptionInput.text.clear()
            refresh()
        }.onFailure {
            Toast.makeText(this, it.message ?: "Valor inválido", Toast.LENGTH_SHORT).show()
        }
    }

    private fun refresh() {
        val cents = LedgerMath.balanceCents(store.entries())
        balanceView.text = "Saldo: R$ %.2f".format(cents / 100.0)
        historyView.removeAllViews()
        store.entries().forEach { entry ->
            val sign = if (entry.kind == MoneyEntry.Kind.INCOME) "+" else "-"
            historyView.addView(TextView(this).apply {
                text = sign + " R$ %.2f · ".format(entry.cents / 100.0) + entry.description
                textSize = 16f
                setPadding(0, 8, 0, 8)
            })
        }
    }

    private fun fieldParams() = LinearLayout.LayoutParams(
        ViewGroup.LayoutParams.MATCH_PARENT,
        ViewGroup.LayoutParams.WRAP_CONTENT
    ).apply { bottomMargin = 8 }

    private fun weightParams() = LinearLayout.LayoutParams(
        0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f
    )
}
