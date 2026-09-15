package com.jsonsoftware.cupuwa

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class ProductMathTest {
    @Test fun computesAccountBalance() {
        val account = Account(10, "Carteira", Account.Type.WALLET, 5000)
        val entries = listOf(
            MoneyEntry(1, 10000, MoneyEntry.Kind.INCOME, "Entrada", accountId = 10),
            MoneyEntry(2, 2500, MoneyEntry.Kind.EXPENSE, "Saída", accountId = 10),
            MoneyEntry(3, 9999, MoneyEntry.Kind.EXPENSE, "Outra conta", accountId = 11),
        )
        assertEquals(12500, ProductMath.accountBalance(account, entries))
    }

    @Test fun computesBudgetProgress() {
        val category = Category(1, "Alimentação", MoneyEntry.Kind.EXPENSE)
        val budget = Budget(1, 1, 10000)
        val now = System.currentTimeMillis()
        val entries = listOf(MoneyEntry(1, 8500, MoneyEntry.Kind.EXPENSE, "Mercado", now, categoryId = 1))
        val progress = ProductMath.budgetProgress(listOf(budget), listOf(category), entries, now).single()
        assertEquals(85, progress.percent); assertEquals(1500, progress.remainingCents)
    }

    @Test fun createsAttentionInsightWhenBudgetIsNearLimit() {
        val category = Category(1, "Lazer", MoneyEntry.Kind.EXPENSE)
        val now = System.currentTimeMillis()
        val entries = listOf(MoneyEntry(1, 9000, MoneyEntry.Kind.EXPENSE, "Cinema", now, categoryId = 1))
        val insights = ProductMath.insights(entries, listOf(Budget(1, 1, 10000)), listOf(category), emptyList(), now)
        assertTrue(insights.any { it.level == FinancialInsight.Level.ATTENTION })
    }
}