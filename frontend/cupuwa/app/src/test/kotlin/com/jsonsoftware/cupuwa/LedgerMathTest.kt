package com.jsonsoftware.cupuwa

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class LedgerMathTest {
    @Test fun parsesBrazilianAmount() {
        assertEquals(2590L, LedgerMath.parseCents("25,90"))
    }

    @Test fun computesIncomeMinusExpense() {
        val entries = listOf(
            MoneyEntry(1L, 10000L, MoneyEntry.Kind.INCOME, "Venda"),
            MoneyEntry(2L, 2500L, MoneyEntry.Kind.EXPENSE, "Compra"),
        )
        assertEquals(7500L, LedgerMath.balanceCents(entries))
    }

    @Test fun rejectsZero() {
        assertFailsWith<IllegalArgumentException> { LedgerMath.parseCents("0") }
    }
}
