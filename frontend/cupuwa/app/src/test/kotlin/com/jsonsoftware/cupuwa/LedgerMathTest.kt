package com.jsonsoftware.cupuwa

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

    @Test fun rejectsZero() {
        assertFailsWith<IllegalArgumentException> { LedgerMath.parseCents("0") }
    }
}
