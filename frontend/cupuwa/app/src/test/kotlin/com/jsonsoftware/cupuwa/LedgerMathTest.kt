package com.jsonsoftware.cupuwa

import java.util.Calendar
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class LedgerMathTest {
    @Test fun parsesBrazilianAmountAsCents() {
        assertEquals(2590L, LedgerMath.parseCents("25,90"))
        assertEquals(2590L, LedgerMath.parseCents("25.90"))
        assertEquals(125090L, LedgerMath.parseCents("1.250,90"))
        assertEquals(2590L, LedgerMath.parseCents("R$ 25,90"))
    }

    @Test fun formatsCentsAsBrazilianReais() {
        assertEquals("R$ 25,90", LedgerMath.formatBrl(2590L))
        assertEquals("R$ 2.590,00", LedgerMath.formatBrl(259000L))
        assertEquals("R$ 1.250,90", LedgerMath.formatBrl(125090L))
        assertEquals("- R$ 25,90", LedgerMath.formatBrl(-2590L))
    }

    @Test fun roundTripDoesNotPromoteCentsToReais() {
        assertEquals("R$ 25,90", LedgerMath.formatBrl(LedgerMath.parseCents("25,90")))
        assertEquals("R$ 2.590,00", LedgerMath.formatBrl(LedgerMath.parseCents("2.590,00")))
    }

    @Test fun computesIncomeMinusExpense() {
        val entries = listOf(
            MoneyEntry(1L, 10000L, MoneyEntry.Kind.INCOME, "Venda"),
            MoneyEntry(2L, 2500L, MoneyEntry.Kind.EXPENSE, "Compra"),
        )
        assertEquals(7500L, LedgerMath.balanceCents(entries))
        assertEquals("R$ 75,00", LedgerMath.formatBrl(7500L))
    }

    @Test fun computesTodayAndMonthTotalsDeterministically() {
        val now = Calendar.getInstance().apply {
            set(2026, Calendar.SEPTEMBER, 14, 12, 0, 0)
            set(Calendar.MILLISECOND, 0)
        }.timeInMillis
        val today = now - 60_000L
        val sameMonth = Calendar.getInstance().apply {
            set(2026, Calendar.SEPTEMBER, 2, 12, 0, 0)
            set(Calendar.MILLISECOND, 0)
        }.timeInMillis
        val previousMonth = Calendar.getInstance().apply {
            set(2026, Calendar.AUGUST, 31, 23, 0, 0)
            set(Calendar.MILLISECOND, 0)
        }.timeInMillis
        val entries = listOf(
            MoneyEntry(1L, 10000L, MoneyEntry.Kind.INCOME, "Hoje", today),
            MoneyEntry(2L, 2500L, MoneyEntry.Kind.EXPENSE, "Hoje", today),
            MoneyEntry(3L, 5000L, MoneyEntry.Kind.INCOME, "Mês", sameMonth),
            MoneyEntry(4L, 1000L, MoneyEntry.Kind.EXPENSE, "Anterior", previousMonth),
        )
        assertEquals(10000L to 2500L, LedgerMath.todayTotals(entries, now))
        assertEquals(15000L to 2500L, LedgerMath.monthTotals(entries, now))
    }

    @Test fun rejectsZero() {
        assertFailsWith<IllegalArgumentException> { LedgerMath.parseCents("0") }
    }
}
