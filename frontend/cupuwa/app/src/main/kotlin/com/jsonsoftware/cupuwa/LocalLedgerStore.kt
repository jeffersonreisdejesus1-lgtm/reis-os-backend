package com.jsonsoftware.cupuwa

import android.content.Context

class LocalLedgerStore(context: Context) {
    private val preferences = context.getSharedPreferences(FILE_NAME, Context.MODE_PRIVATE)

    fun entries(): List<MoneyEntry> =
        preferences.getString(KEY_ENTRIES, null)
            .orEmpty()
            .split(RECORD_SEPARATOR)
            .filter { it.isNotBlank() }
            .mapNotNull { row ->
                val fields = row.split(FIELD_SEPARATOR)
                if (fields.size !in 4..5) return@mapNotNull null
                runCatching {
                    MoneyEntry(
                        id = fields[0].toLong(),
                        cents = fields[1].toLong(),
                        kind = MoneyEntry.Kind.valueOf(fields[2]),
                        description = fields[3],
                        createdAtMillis = fields.getOrNull(4)?.toLongOrNull() ?: fields[0].toLong(),
                    )
                }.getOrNull()
            }
            .sortedByDescending { it.createdAtMillis }

    fun add(cents: Long, kind: MoneyEntry.Kind, description: String): MoneyEntry {
        val now = System.currentTimeMillis()
        val entry = MoneyEntry(
            id = now,
            cents = cents,
            kind = kind,
            description = defaultDescription(kind, description),
            createdAtMillis = now,
        )
        persist(listOf(entry) + entries())
        return entry
    }

    fun get(id: Long): MoneyEntry? = entries().firstOrNull { it.id == id }

    fun update(id: Long, cents: Long, kind: MoneyEntry.Kind, description: String) {
        val current = entries()
        require(current.any { it.id == id }) { "Lançamento não encontrado" }
        persist(
            current.map { entry ->
                if (entry.id == id) {
                    entry.copy(
                        cents = cents,
                        kind = kind,
                        description = defaultDescription(kind, description),
                    )
                } else {
                    entry
                }
            },
        )
    }

    fun delete(id: Long) {
        val current = entries()
        val remaining = current.filterNot { it.id == id }
        require(remaining.size != current.size) { "Lançamento não encontrado" }
        persist(remaining)
    }

    private fun persist(items: List<MoneyEntry>) {
        val encoded = items.joinToString(RECORD_SEPARATOR) {
            listOf(it.id, it.cents, it.kind.name, it.description, it.createdAtMillis)
                .joinToString(FIELD_SEPARATOR)
        }
        preferences.edit().putString(KEY_ENTRIES, encoded).commit()
    }

    private fun defaultDescription(kind: MoneyEntry.Kind, description: String): String =
        description.ifBlank { if (kind == MoneyEntry.Kind.INCOME) "Entrada" else "Saída" }

    private companion object {
        const val FILE_NAME = "cupuwa_local_ledger"
        const val KEY_ENTRIES = "entries.v1"
        const val RECORD_SEPARATOR = "\u001e"
        const val FIELD_SEPARATOR = "\u001f"
    }
}
