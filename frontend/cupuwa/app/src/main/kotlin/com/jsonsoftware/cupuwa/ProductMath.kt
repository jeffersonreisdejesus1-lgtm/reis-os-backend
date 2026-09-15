package com.jsonsoftware.cupuwa

object ProductMath {
    fun accountBalance(account: Account, entries: List<MoneyEntry>): Long =
        account.openingBalanceCents + entries.filter { it.accountId == account.id }.sumOf {
            if (it.kind == MoneyEntry.Kind.INCOME) it.cents else -it.cents
        }

    fun categoryTotals(entries: List<MoneyEntry>, kind: MoneyEntry.Kind): Map<Long, Long> =
        entries.filter { it.kind == kind && it.categoryId != null }
            .groupBy { it.categoryId!! }
            .mapValues { (_, values) -> values.sumOf { it.cents } }

    fun budgetProgress(
        budgets: List<Budget>, categories: List<Category>, entries: List<MoneyEntry>, now: Long = System.currentTimeMillis(),
    ): List<BudgetProgress> {
        val monthEntries = entries.filter { it.createdAtMillis >= LedgerMath.startOfMonthMillis(now) }
        val expenses = categoryTotals(monthEntries, MoneyEntry.Kind.EXPENSE)
        return budgets.map { budget ->
            BudgetProgress(budget, categories.firstOrNull { it.id == budget.categoryId }, expenses[budget.categoryId] ?: 0)
        }.sortedByDescending { it.percent }
    }

    fun insights(
        entries: List<MoneyEntry>, budgets: List<Budget>, categories: List<Category>, goals: List<Goal>, now: Long = System.currentTimeMillis(),
    ): List<FinancialInsight> {
        val result = mutableListOf<FinancialInsight>()
        val (income, expense) = LedgerMath.monthTotals(entries, now)
        if (income == 0L && expense == 0L) {
            result += FinancialInsight("Comece pelo seu mês", "Registre movimentações para o CUPUWA montar sua leitura financeira.", FinancialInsight.Level.NEUTRAL)
        } else if (expense > income) {
            result += FinancialInsight("Mês em atenção", "Suas saídas estão ${LedgerMath.formatBrl(expense - income)} acima das entradas.", FinancialInsight.Level.ATTENTION)
        } else {
            result += FinancialInsight("Mês positivo", "Você está ${LedgerMath.formatBrl(income - expense)} acima das saídas neste mês.", FinancialInsight.Level.POSITIVE)
        }
        budgetProgress(budgets, categories, entries, now).firstOrNull { it.percent >= 80 }?.let {
            result += FinancialInsight(
                if (it.percent >= 100) "Orçamento ultrapassado" else "Orçamento perto do limite",
                "${it.category?.name ?: "Categoria"}: ${it.percent}% do limite usado.",
                FinancialInsight.Level.ATTENTION,
            )
        }
        goals.filter { it.targetCents > 0 }.maxByOrNull { (it.savedCents * 100) / it.targetCents }?.let {
            val pct = ((it.savedCents * 100) / it.targetCents).coerceIn(0, 100)
            result += FinancialInsight("Meta em andamento", "${it.name}: $pct% concluída.", FinancialInsight.Level.POSITIVE)
        }
        return result.take(3)
    }
}