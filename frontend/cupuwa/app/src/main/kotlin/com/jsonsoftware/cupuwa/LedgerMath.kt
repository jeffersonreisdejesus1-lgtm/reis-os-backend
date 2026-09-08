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
        val trimmed = raw.trim()
        require(trimmed.isNotEmpty()) { "Valor obrigatório" }
        val normalized = when {
            trimmed.contains(',') && trimmed.contains('.') ->
                trimmed.replace(".", "").replace(',', '.')
            trimmed.contains(',') ->
                trimmed.replace(',', '.')
            else -> trimmed
        }
        require(normalized.matches(Regex("\\d+(\\.\\d{1,2})?"))) { "Valor inválido" }
        return BigDecimal(normalized)
            .setScale(2, RoundingMode.HALF_UP)
            .movePointRight(2)
            .longValueExact()
            .also { require(it > 0) { "O valor deve ser maior que zero" } }
    }

    fun formatBrl(cents: Long): String {
        val sign = if (cents < 0) "- " else ""
        val abs = kotlin.math.abs(cents)
        return "%sR$ %d,%02d".format(sign, abs / 100, abs % 100)
    }

    fun balanceCents(entries: List<MoneyEntry>): Long =
        entries.sumOf { if (it.kind == MoneyEntry.Kind.INCOME) it.cents else -it.cents }
}
