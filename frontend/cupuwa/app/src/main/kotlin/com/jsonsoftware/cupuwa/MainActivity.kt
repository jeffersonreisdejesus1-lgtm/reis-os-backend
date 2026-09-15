package com.jsonsoftware.cupuwa

import android.os.Bundle
import android.content.Intent
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import android.widget.Toast
import android.widget.ArrayAdapter
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
    private lateinit var product: ProductStore
    private lateinit var adapter: MovementAdapter
    private var editingId: Long? = null
    private var categories: List<Category> = emptyList()
    private var saveInProgress = false

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        product = ProductStore(this)
        if (!product.profile().onboardingComplete) {
            startActivity(Intent(this, OnboardingActivity::class.java))
            finish()
            return
        }
        setContentView(R.layout.activity_home)
        store = LocalLedgerStore(this)
        adapter = MovementAdapter({ startEdit(it) }, { confirmDelete(it) })
        findViewById<RecyclerView>(R.id.historyList).apply { layoutManager = LinearLayoutManager(this@MainActivity); adapter = this@MainActivity.adapter }
        findViewById<MaterialButton>(R.id.incomeButton).setOnClickListener { save(MoneyEntry.Kind.INCOME) }
        findViewById<MaterialButton>(R.id.expenseButton).setOnClickListener { save(MoneyEntry.Kind.EXPENSE) }
        findViewById<MaterialButton>(R.id.cancelEditButton).setOnClickListener { clearEditor() }
        findViewById<MaterialButton>(R.id.navHome).setOnClickListener { }
        findViewById<MaterialButton>(R.id.navMovements).setOnClickListener { startActivity(Intent(this, MovementActivity::class.java)) }
        findViewById<MaterialButton>(R.id.navPlan).setOnClickListener { startActivity(Intent(this, SectionActivity::class.java).putExtra(SectionActivity.EXTRA_SECTION, SectionActivity.PLAN)) }
        findViewById<MaterialButton>(R.id.navInsights).setOnClickListener { startActivity(Intent(this, SectionActivity::class.java).putExtra(SectionActivity.EXTRA_SECTION, SectionActivity.INSIGHTS)) }
        findViewById<MaterialButton>(R.id.navSettings).setOnClickListener { startActivity(Intent(this, SectionActivity::class.java).putExtra(SectionActivity.EXTRA_SECTION, SectionActivity.SETTINGS)) }
        categories = product.categories()
        findViewById<com.google.android.material.textfield.MaterialAutoCompleteTextView>(R.id.categoryInput).apply {
            setAdapter(ArrayAdapter(context, android.R.layout.simple_dropdown_item_1line, categories.filter { it.kind == MoneyEntry.Kind.EXPENSE }.map { it.name }))
            setText(categories.firstOrNull { it.kind == MoneyEntry.Kind.EXPENSE }?.name, false)
        }
        refresh()
    }

    private fun save(kind: MoneyEntry.Kind) {
        if (saveInProgress) return
        saveInProgress = true
        val incomeButton = findViewById<MaterialButton>(R.id.incomeButton)
        val expenseButton = findViewById<MaterialButton>(R.id.expenseButton)
        incomeButton.isEnabled = false
        expenseButton.isEnabled = false
        val amount = findViewById<TextInputEditText>(R.id.amountInput); val description = findViewById<TextInputEditText>(R.id.descriptionInput)
        runCatching {
            val cents = LedgerMath.parseCents(amount.text?.toString().orEmpty()); val note = description.text?.toString().orEmpty().trim()
            val selectedName = findViewById<com.google.android.material.textfield.MaterialAutoCompleteTextView>(R.id.categoryInput).text?.toString().orEmpty()
            val categoryId = categories.firstOrNull { it.name == selectedName && it.kind == kind }?.id
            val accountId = product.activeAccountId()
            val id = editingId; if (id == null) store.add(cents, kind, note, accountId = accountId, categoryId = categoryId) else store.update(id, cents, kind, note, accountId = accountId, categoryId = categoryId)
            clearEditor(); refresh()
        }.onFailure { Toast.makeText(this, it.message ?: getString(R.string.invalid_value), Toast.LENGTH_SHORT).show() }
        saveInProgress = false
        incomeButton.isEnabled = true
        expenseButton.isEnabled = true
    }

    private fun startEdit(entry: MoneyEntry) {
        editingId = entry.id
        findViewById<TextInputEditText>(R.id.amountInput).setText(LedgerMath.formatBrl(entry.cents).removePrefix("- ").removePrefix("R$ ").trim())
        findViewById<TextInputEditText>(R.id.descriptionInput).setText(entry.description)
        findViewById<TextView>(R.id.composerTitle).text = getString(R.string.edit_entry); findViewById<MaterialButton>(R.id.cancelEditButton).visibility = View.VISIBLE
        findViewById<com.google.android.material.textfield.MaterialAutoCompleteTextView>(R.id.categoryInput).setText(categories.firstOrNull { it.id == entry.categoryId }?.name ?: "", false)
    }
    private fun clearEditor() { editingId = null; findViewById<TextInputEditText>(R.id.amountInput).text?.clear(); findViewById<TextInputEditText>(R.id.descriptionInput).text?.clear(); findViewById<com.google.android.material.textfield.MaterialAutoCompleteTextView>(R.id.categoryInput).setText(categories.firstOrNull { it.kind == MoneyEntry.Kind.EXPENSE }?.name ?: "", false); findViewById<TextView>(R.id.composerTitle).text = getString(R.string.new_entry); findViewById<MaterialButton>(R.id.cancelEditButton).visibility = View.GONE }

    private fun refresh() {
        val entries = store.entries(); val profile = product.profile(); val accounts = product.accounts(); val categories = product.categories(); val budgets = product.budgets(); val goals = product.goals()
        findViewById<TextView>(R.id.greetingView).text = if (profile.name.isBlank()) "CUPUWA" else "Olá, ${profile.name}"
        val opening = accounts.filterNot { it.archived }.sumOf { it.openingBalanceCents }
        findViewById<TextView>(R.id.balanceView).text = LedgerMath.formatBrl(opening + LedgerMath.balanceCents(entries))
        val (todayIncome, todayExpense) = LedgerMath.todayTotals(entries); findViewById<TextView>(R.id.todayView).text = "Hoje · +${LedgerMath.formatBrl(todayIncome)} · -${LedgerMath.formatBrl(todayExpense)}"
        val (income, expense) = LedgerMath.monthTotals(entries); findViewById<TextView>(R.id.monthView).text = getString(R.string.summary_values, LedgerMath.formatBrl(income), LedgerMath.formatBrl(expense)); findViewById<TextView>(R.id.monthResultView).text = "Resultado ${LedgerMath.formatBrl(income - expense)}"
        val insights = ProductMath.insights(entries, budgets, categories, goals); findViewById<TextView>(R.id.insightView).text = insights.joinToString("\n\n") { "${it.title}\n${it.detail}" }
        val bp = ProductMath.budgetProgress(budgets, categories, entries)
        findViewById<TextView>(R.id.planningView).text = buildString {
            if (bp.isEmpty()) append(getString(R.string.budget_empty)) else append(bp.take(3).joinToString("\n") { "${it.category?.name ?: "Categoria"}: ${it.percent}% · resta ${LedgerMath.formatBrl(it.remainingCents)}" })
            append("\n\n")
            if (goals.isEmpty()) append(getString(R.string.goal_empty)) else append(goals.take(2).joinToString("\n") { "${it.name}: ${LedgerMath.formatBrl(it.savedCents)} de ${LedgerMath.formatBrl(it.targetCents)}" })
        }
        findViewById<TextView>(R.id.emptyView).visibility = if (entries.isEmpty()) View.VISIBLE else View.GONE; adapter.submit(entries)
    }

    private fun confirmDelete(entry: MoneyEntry) { AlertDialog.Builder(this).setTitle(R.string.delete_title).setMessage("${LedgerMath.formatBrl(entry.cents)} · ${entry.description}").setNegativeButton(R.string.cancel, null).setPositiveButton(R.string.delete) { _, _ -> store.delete(entry.id); if (editingId == entry.id) clearEditor(); refresh() }.show() }
}

class MovementAdapter(private val onEdit: (MoneyEntry) -> Unit, private val onDelete: (MoneyEntry) -> Unit) : RecyclerView.Adapter<MovementAdapter.Holder>() {
    private var items = emptyList<MoneyEntry>(); private val time = SimpleDateFormat("dd/MM · HH:mm", Locale("pt", "BR"))
    fun submit(value: List<MoneyEntry>) { items = value; notifyDataSetChanged() }
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) = Holder(LayoutInflater.from(parent.context).inflate(R.layout.item_movement, parent, false))
    override fun getItemCount() = items.size
    override fun onBindViewHolder(h: Holder, position: Int) { val e = items[position]; val income = e.kind == MoneyEntry.Kind.INCOME; h.description.text = e.description; h.meta.text = time.format(Date(e.createdAtMillis)) + if (income) " · entrada" else " · saída"; h.amount.text = (if (income) "+ " else "- ") + LedgerMath.formatBrl(e.cents); h.amount.setTextColor(h.itemView.context.getColor(if (income) R.color.cupuwa_income else R.color.cupuwa_expense)); h.edit.setOnClickListener { onEdit(e) }; h.delete.setOnClickListener { onDelete(e) } }
    class Holder(view: View) : RecyclerView.ViewHolder(view) { val description: TextView = view.findViewById(R.id.itemDescription); val meta: TextView = view.findViewById(R.id.itemMeta); val amount: TextView = view.findViewById(R.id.itemAmount); val edit: MaterialButton = view.findViewById(R.id.editButton); val delete: MaterialButton = view.findViewById(R.id.deleteButton) }
}

