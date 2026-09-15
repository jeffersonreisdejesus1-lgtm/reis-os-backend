package com.jsonsoftware.cupuwa

import java.math.BigDecimal
import java.math.RoundingMode
import java.util.Calendar

data class MoneyEntry(
    val id: Long,
    val cents: Long,
    val kind: Kind,
    val description: String,
    val createdAtMillis: Long = id,
    val accountId: Long? = null,
    val categoryId: Long? = null,
) {
    enum class Kind { INCOME, EXPENSE }
}

object LedgerMath {
    fun parseCents(raw: String): Long {
        val trimmed = raw.trim().replace("R$", "", ignoreCase = true).replace(" ", "")
        require(trimmed.isNotEmpty()) { "Valor obrigatório" }
        val normalized = when {
            trimmed.contains(',') && trimmed.contains('.') -> trimmed.replace(".", "").replace(',', '.')
            trimmed.contains(',') -> trimmed.replace(',', '.')
            else -> trimmed
        }
        require(normalized.matches(Regex("\\d+(\\.\\d{1,2})?"))) { "Valor inválido" }
        return BigDecimal(normalized).setScale(2, RoundingMode.HALF_UP).movePointRight(2).longValueExact()
            .also { require(it > 0) { "O valor deve ser maior que zero" } }
    }

    fun formatBrl(cents: Long): String {
        val sign = if (cents < 0) "- " else ""
        val abs = kotlin.math.abs(cents)
        val whole = abs / 100
        val frac = abs % 100
        val grouped = whole.toString().reversed().chunked(3).joinToString(".").reversed()
        return "%sR$ %s,%02d".format(sign, grouped, frac)
    }

    fun balanceCents(entries: List<MoneyEntry>): Long = entries.sumOf {
        if (it.kind == MoneyEntry.Kind.INCOME) it.cents else -it.cents
    }

    fun startOfDayMillis(now: Long = System.currentTimeMillis()): Long {
        val cal = Calendar.getInstance(); cal.timeInMillis = now
        cal.set(Calendar.HOUR_OF_DAY, 0); cal.set(Calendar.MINUTE, 0); cal.set(Calendar.SECOND, 0); cal.set(Calendar.MILLISECOND, 0)
        return cal.timeInMillis
    }

    fun startOfMonthMillis(now: Long = System.currentTimeMillis()): Long {
        val cal = Calendar.getInstance(); cal.timeInMillis = now
        cal.set(Calendar.DAY_OF_MONTH, 1); cal.set(Calendar.HOUR_OF_DAY, 0); cal.set(Calendar.MINUTE, 0); cal.set(Calendar.SECOND, 0); cal.set(Calendar.MILLISECOND, 0)
        return cal.timeInMillis
    }

    fun totalsSince(entries: List<MoneyEntry>, startMillis: Long): Pair<Long, Long> {
        val scoped = entries.filter { it.createdAtMillis >= startMillis }
        return scoped.filter { it.kind == MoneyEntry.Kind.INCOME }.sumOf { it.cents } to
            scoped.filter { it.kind == MoneyEntry.Kind.EXPENSE }.sumOf { it.cents }
    }

    fun todayTotals(entries: List<MoneyEntry>, now: Long = System.currentTimeMillis()) = totalsSince(entries, startOfDayMillis(now))
    fun monthTotals(entries: List<MoneyEntry>, now: Long = System.currentTimeMillis()) = totalsSince(entries, startOfMonthMillis(now))
}