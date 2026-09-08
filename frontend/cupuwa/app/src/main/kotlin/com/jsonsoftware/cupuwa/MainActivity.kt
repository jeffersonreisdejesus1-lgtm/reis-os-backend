package com.jsonsoftware.cupuwa

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.button.MaterialButton
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : AppCompatActivity() {
    private lateinit var store: LocalLedgerStore
    private lateinit var adapter: MovementAdapter

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        setContentView(R.layout.activity_home)
        store = LocalLedgerStore(this)
        adapter = MovementAdapter(
            onEdit = { openMovement(it.kind, it.id) },
            onDelete = { confirmDelete(it) },
        )
        findViewById<RecyclerView>(R.id.historyList).apply {
            layoutManager = LinearLayoutManager(this@MainActivity)
            adapter = this@MainActivity.adapter
        }
        findViewById<MaterialButton>(R.id.incomeButton).setOnClickListener {
            openMovement(MoneyEntry.Kind.INCOME, null)
        }
        findViewById<MaterialButton>(R.id.expenseButton).setOnClickListener {
            openMovement(MoneyEntry.Kind.EXPENSE, null)
        }
    }

    override fun onResume() {
        super.onResume()
        refresh()
    }

    private fun refresh() {
        val entries = store.entries()
        findViewById<TextView>(R.id.balanceView).text = LedgerMath.formatBrl(LedgerMath.balanceCents(entries))
        val (income, expense) = LedgerMath.todayTotals(entries)
        findViewById<TextView>(R.id.todayView).text =
            "Hoje  + ${LedgerMath.formatBrl(income)}   - ${LedgerMath.formatBrl(expense)}"
        findViewById<TextView>(R.id.emptyView).visibility =
            if (entries.isEmpty()) View.VISIBLE else View.GONE
        adapter.submit(entries)
    }

    private fun openMovement(kind: MoneyEntry.Kind, id: Long?) {
        startActivity(
            Intent(this, MovementActivity::class.java)
                .putExtra(MovementActivity.EXTRA_KIND, kind.name)
                .putExtra(MovementActivity.EXTRA_ID, id ?: -1L),
        )
    }

    private fun confirmDelete(entry: MoneyEntry) {
        AlertDialog.Builder(this)
            .setTitle(R.string.delete_title)
            .setMessage("${LedgerMath.formatBrl(entry.cents)} · ${entry.description}")
            .setNegativeButton(R.string.cancel, null)
            .setPositiveButton(R.string.delete) { _, _ ->
                store.delete(entry.id)
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
