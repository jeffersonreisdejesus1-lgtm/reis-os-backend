package com.jsonsoftware.cupuwa

import java.math.BigDecimal
import java.math.RoundingMode
import android.widget.EditText
import android.text.method.DigitsKeyListener
import java.util.Calendar

data class MoneyEntry(
    val id: Long,
    val cents: Long,
    val kind: Kind,
    val description: String,
    val createdAtMillis: Long = id,
    val accountId: Long? = null,
    val categoryId: Long? = null,
    val operationId: String = id.toString(),
) {
    enum class Kind { INCOME, EXPENSE }
}

object LedgerMath {
    fun parseCents(raw: String): Long = parse(raw, allowZero = false)

    fun parseCentsAllowZero(raw: String): Long = parse(raw, allowZero = true)

    private fun parse(raw: String, allowZero: Boolean): Long {
        val trimmed = raw.trim().replace("R$", "", ignoreCase = true).replace(" ", "")
        require(trimmed.isNotEmpty()) { "Valor obrigatório" }
        require(!trimmed.startsWith("-") && !trimmed.startsWith("+")) { "Valor inválido" }

        val normalized = when {
            trimmed.contains(",") && trimmed.contains(".") -> {
                val decimal = maxOf(trimmed.lastIndexOf(','), trimmed.lastIndexOf('.'))
                val integer = trimmed.substring(0, decimal).replace(",", "").replace(".", "")
                val fraction = trimmed.substring(decimal + 1)
                require(fraction.length in 1..2) { "Use no máximo duas casas decimais" }
                "$integer.$fraction"
            }
            trimmed.count { it == ',' } > 1 || trimmed.count { it == '.' } > 1 -> {
                if (trimmed.matches(Regex("\\d{1,3}(\\.\\d{3})+"))) trimmed.replace(".", "")
                else error("Valor inválido")
            }
            trimmed.contains(',') -> {
                val fraction = trimmed.substringAfter(',')
                require(fraction.length in 0..2) { "Use no máximo duas casas decimais" }
                trimmed.replace(',', '.').let { if (it.endsWith(".")) it + "0" else it }
            }
            trimmed.contains('.') -> {
                val fraction = trimmed.substringAfter('.')
                if (fraction.length == 3 && trimmed.substringBefore('.').length in 1..3) trimmed.replace(".", "")
                else {
                    require(fraction.length in 0..2) { "Use no máximo duas casas decimais" }
                    if (trimmed.endsWith(".")) trimmed + "0" else trimmed
                }
            }
            else -> trimmed
        }
        require(normalized.matches(Regex("\\d+(\\.\\d{1,2})?"))) { "Valor inválido" }
        val cents = BigDecimal(normalized).setScale(2, RoundingMode.UNNECESSARY).movePointRight(2).longValueExact()
        require(allowZero || cents > 0) { "O valor deve ser maior que zero" }
        return cents
    }

    fun configureMoneyInput(editText: EditText) {
        editText.keyListener = DigitsKeyListener.getInstance("0123456789,.")
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