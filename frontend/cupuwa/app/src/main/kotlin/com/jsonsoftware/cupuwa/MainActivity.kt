package com.jsonsoftware.cupuwa

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : AppCompatActivity() {
    private lateinit var store: LocalLedgerStore
    private lateinit var adapter: MovementAdapter
    private var editingId: Long? = null

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        setContentView(R.layout.activity_home)
        store = LocalLedgerStore(this)
        adapter = MovementAdapter(
            onEdit = { startEdit(it) },
            onDelete = { confirmDelete(it) },
        )
        findViewById<RecyclerView>(R.id.historyList).apply {
            layoutManager = LinearLayoutManager(this@MainActivity)
            adapter = this@MainActivity.adapter
        }
        findViewById<MaterialButton>(R.id.incomeButton).setOnClickListener {
            save(MoneyEntry.Kind.INCOME)
        }
        findViewById<MaterialButton>(R.id.expenseButton).setOnClickListener {
            save(MoneyEntry.Kind.EXPENSE)
        }
        findViewById<MaterialButton>(R.id.cancelEditButton).setOnClickListener { clearEditor() }
        refresh()
    }

    private fun save(kind: MoneyEntry.Kind) {
        val amount = findViewById<TextInputEditText>(R.id.amountInput)
        val description = findViewById<TextInputEditText>(R.id.descriptionInput)
        runCatching {
            val cents = LedgerMath.parseCents(amount.text?.toString().orEmpty())
            val note = description.text?.toString().orEmpty().trim().ifBlank { getString(R.string.no_description) }
            val id = editingId
            if (id == null) store.add(cents, kind, note)
            else store.update(id, cents, kind, note)
            clearEditor()
            refresh()
        }.onFailure {
            Toast.makeText(this, it.message ?: getString(R.string.invalid_value), Toast.LENGTH_SHORT).show()
        }
    }

    private fun startEdit(entry: MoneyEntry) {
        editingId = entry.id
        findViewById<TextInputEditText>(R.id.amountInput).setText(
            LedgerMath.formatBrl(entry.cents).removePrefix("- ").removePrefix("R$ ").trim(),
        )
        findViewById<TextInputEditText>(R.id.descriptionInput).setText(entry.description)
        findViewById<TextView>(R.id.composerTitle).text = getString(R.string.edit_entry)
        findViewById<MaterialButton>(R.id.cancelEditButton).visibility = View.VISIBLE
    }

    private fun clearEditor() {
        editingId = null
        findViewById<TextInputEditText>(R.id.amountInput).text?.clear()
        findViewById<TextInputEditText>(R.id.descriptionInput).text?.clear()
        findViewById<TextView>(R.id.composerTitle).text = getString(R.string.new_entry)
        findViewById<MaterialButton>(R.id.cancelEditButton).visibility = View.GONE
    }

    private fun refresh() {
        val entries = store.entries()
        findViewById<TextView>(R.id.balanceView).text = LedgerMath.formatBrl(LedgerMath.balanceCents(entries))

        val (todayIncome, todayExpense) = LedgerMath.todayTotals(entries)
        findViewById<TextView>(R.id.todayView).text = getString(
            R.string.summary_values,
            LedgerMath.formatBrl(todayIncome),
            LedgerMath.formatBrl(todayExpense),
        )

        val (monthIncome, monthExpense) = LedgerMath.monthTotals(entries)
        findViewById<TextView>(R.id.monthView).text = getString(
            R.string.summary_values,
            LedgerMath.formatBrl(monthIncome),
            LedgerMath.formatBrl(monthExpense),
        )
        findViewById<TextView>(R.id.monthResultView).text = LedgerMath.formatBrl(monthIncome - monthExpense)

        findViewById<TextView>(R.id.emptyView).visibility =
            if (entries.isEmpty()) View.VISIBLE else View.GONE
        adapter.submit(entries)
    }

    private fun confirmDelete(entry: MoneyEntry) {
        AlertDialog.Builder(this)
            .setTitle(R.string.delete_title)
            .setMessage("${LedgerMath.formatBrl(entry.cents)} · ${entry.description}")
            .setNegativeButton(R.string.cancel, null)
            .setPositiveButton(R.string.delete) { _, _ ->
                store.delete(entry.id)
                if (editingId == entry.id) clearEditor()
                refresh()
            }
            .show()
    }
}

class MovementAdapter(
    private val onEdit: (MoneyEntry) -> Unit,
    private val onDelete: (MoneyEntry) -> Unit,
) : RecyclerView.Adapter<MovementAdapter.Holder>() {
    private var items: List<MoneyEntry> = emptyList()
    private val time = SimpleDateFormat("dd/MM · HH:mm", Locale("pt", "BR"))

    fun submit(value: List<MoneyEntry>) {
        items = value
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): Holder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_movement, parent, false)
        return Holder(view)
    }

    override fun getItemCount(): Int = items.size

    override fun onBindViewHolder(holder: Holder, position: Int) {
        val entry = items[position]
        val income = entry.kind == MoneyEntry.Kind.INCOME
        holder.description.text = entry.description
        holder.meta.text = time.format(Date(entry.createdAtMillis)) +
            if (income) " · entrada" else " · saída"
        holder.amount.text = (if (income) "+ " else "- ") + LedgerMath.formatBrl(entry.cents)
        holder.amount.setTextColor(
            holder.itemView.context.getColor(if (income) R.color.cupuwa_income else R.color.cupuwa_expense),
        )
        holder.edit.setOnClickListener { onEdit(entry) }
        holder.delete.setOnClickListener { onDelete(entry) }
    }

    class Holder(view: View) : RecyclerView.ViewHolder(view) {
        val description: TextView = view.findViewById(R.id.itemDescription)
        val meta: TextView = view.findViewById(R.id.itemMeta)
        val amount: TextView = view.findViewById(R.id.itemAmount)
        val edit: MaterialButton = view.findViewById(R.id.editButton)
        val delete: MaterialButton = view.findViewById(R.id.deleteButton)
    }
}
