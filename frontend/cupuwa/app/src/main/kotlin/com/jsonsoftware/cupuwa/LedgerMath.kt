package com.jsonsoftware.cupuwa

import java.math.BigDecimal
import java.math.RoundingMode

data class MoneyEntry(
    val id: Long,
    val cents: Long,
    val kind: Kind,
    val description: String,
) {
    enum class Kind { INCOME, EXPENSE }
}

object LedgerMath {
    fun parseCents(raw: String): Long {
        val normalized = raw.trim().replace(",", ".")
        require(normalized.isNotEmpty()) { "Valor obrigatório" }
        return BigDecimal(normalized)
            .setScale(2, RoundingMode.HALF_UP)
            .movePointRight(2)
            .longValueExact()
            .also { require(it > 0) { "O valor deve ser maior que zero" } }
    }

    fun balanceCents(entries: List<MoneyEntry>): Long =
        entries.sumOf { if (it.kind == MoneyEntry.Kind.INCOME) it.cents else -it.cents }
}
