package com.jsonsoftware.cupuwa

data class Account(
    val id: Long,
    val name: String,
    val type: Type,
    val openingBalanceCents: Long = 0,
    val archived: Boolean = false,
) {
    enum class Type { CASH, CHECKING, SAVINGS, WALLET, OTHER }
}

data class Category(
    val id: Long,
    val name: String,
    val kind: MoneyEntry.Kind,
)

data class Budget(
    val id: Long,
    val categoryId: Long,
    val limitCents: Long,
)

data class Goal(
    val id: Long,
    val name: String,
    val targetCents: Long,
    val savedCents: Long = 0,
)

data class LocalProfile(
    val name: String = "",
    val monthlyIncomeCents: Long = 0,
    val onboardingComplete: Boolean = false,
)

data class BudgetProgress(
    val budget: Budget,
    val category: Category?,
    val spentCents: Long,
) {
    val remainingCents: Long get() = budget.limitCents - spentCents
    val percent: Int get() = if (budget.limitCents <= 0) 0 else
        ((spentCents * 100) / budget.limitCents).coerceIn(0, 999).toInt()
}

data class FinancialInsight(val title: String, val detail: String, val level: Level) {
    enum class Level { POSITIVE, NEUTRAL, ATTENTION }
}