package com.jsonsoftware.cupuwa

import android.content.Context

class ProductStore(context: Context) {
    private val p = context.getSharedPreferences("cupuwa_product_v1", Context.MODE_PRIVATE)
    private val rs = "\u001e"; private val fs = "\u001f"

    fun profile(): LocalProfile {
        val f = p.getString("profile", "")!!.split(fs)
        return if (f.size == 3) LocalProfile(f[0], f[1].toLongOrNull() ?: 0, f[2] == "1") else LocalProfile()
    }
    fun saveProfile(value: LocalProfile) { p.edit().putString("profile", listOf(value.name, value.monthlyIncomeCents, if (value.onboardingComplete) 1 else 0).joinToString(fs)).commit() }

    fun accounts(): List<Account> = decode("accounts") { f -> Account(f[0].toLong(), f[1], Account.Type.valueOf(f[2]), f[3].toLong(), f.getOrNull(4) == "1") }
    fun saveAccount(name: String, type: Account.Type, opening: Long): Account {
        val current = accounts(); val item = Account(nextId(), name.trim().ifBlank { "Minha conta" }, type, opening)
        encode("accounts", current + item) { listOf(it.id, it.name, it.type.name, it.openingBalanceCents, if (it.archived) 1 else 0) }; return item
    }
    fun archiveAccount(id: Long) { encode("accounts", accounts().map { if (it.id == id) it.copy(archived = true) else it }) { listOf(it.id, it.name, it.type.name, it.openingBalanceCents, if (it.archived) 1 else 0) } }

    fun categories(): List<Category> {
        val saved = decode("categories") { f -> Category(f[0].toLong(), f[1], MoneyEntry.Kind.valueOf(f[2])) }
        return if (saved.isNotEmpty()) saved else defaultCategories().also { values -> encode("categories", values) { listOf(it.id, it.name, it.kind.name) } }
    }
    fun saveCategory(name: String, kind: MoneyEntry.Kind): Category {
        val item = Category(nextId(), name.trim(), kind); require(item.name.isNotBlank()) { "Nome obrigatório" }
        encode("categories", categories() + item) { listOf(it.id, it.name, it.kind.name) }; return item
    }

    fun budgets(): List<Budget> = decode("budgets") { f -> Budget(f[0].toLong(), f[1].toLong(), f[2].toLong()) }
    fun saveBudget(categoryId: Long, limit: Long) {
        require(limit > 0); val current = budgets().filterNot { it.categoryId == categoryId }
        encode("budgets", current + Budget(nextId(), categoryId, limit)) { listOf(it.id, it.categoryId, it.limitCents) }
    }

    fun goals(): List<Goal> = decode("goals") { f -> Goal(f[0].toLong(), f[1], f[2].toLong(), f[3].toLong()) }
    fun saveGoal(name: String, target: Long) {
        require(name.isNotBlank() && target > 0); encode("goals", goals() + Goal(nextId(), name.trim(), target)) { listOf(it.id, it.name, it.targetCents, it.savedCents) }
    }
    fun contribute(goalId: Long, amount: Long) {
        require(amount > 0); encode("goals", goals().map { if (it.id == goalId) it.copy(savedCents = (it.savedCents + amount).coerceAtMost(it.targetCents)) else it }) { listOf(it.id, it.name, it.targetCents, it.savedCents) }
    }

    fun clearAll() { p.edit().clear().commit() }

    private fun defaultCategories() = listOf(
        Category(101, "Moradia", MoneyEntry.Kind.EXPENSE), Category(102, "Alimentação", MoneyEntry.Kind.EXPENSE),
        Category(103, "Transporte", MoneyEntry.Kind.EXPENSE), Category(104, "Saúde", MoneyEntry.Kind.EXPENSE),
        Category(105, "Lazer", MoneyEntry.Kind.EXPENSE), Category(106, "Contas", MoneyEntry.Kind.EXPENSE),
        Category(201, "Salário", MoneyEntry.Kind.INCOME), Category(202, "Freelance", MoneyEntry.Kind.INCOME),
        Category(203, "Outras entradas", MoneyEntry.Kind.INCOME),
    )
    private fun nextId() = System.nanoTime()
    private fun <T> decode(key: String, make: (List<String>) -> T): List<T> = p.getString(key, "").orEmpty().split(rs).filter { it.isNotBlank() }.mapNotNull { runCatching { make(it.split(fs)) }.getOrNull() }
    private fun <T> encode(key: String, values: List<T>, fields: (T) -> List<Any>) { p.edit().putString(key, values.joinToString(rs) { fields(it).joinToString(fs) }).commit() }
}