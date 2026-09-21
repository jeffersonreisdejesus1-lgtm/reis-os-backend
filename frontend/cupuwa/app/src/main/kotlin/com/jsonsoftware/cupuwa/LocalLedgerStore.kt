package com.jsonsoftware.cupuwa

import android.content.Context
import java.util.UUID

class LocalLedgerStore(context: Context) {
    private val preferences = context.getSharedPreferences(FILE_NAME, Context.MODE_PRIVATE)

    fun entries(): List<MoneyEntry> = preferences.getString(KEY_ENTRIES, null).orEmpty()
        .split(RECORD_SEPARATOR).filter { it.isNotBlank() }.mapNotNull { row ->
            val f = row.split(FIELD_SEPARATOR)
            if (f.size !in 4..8) return@mapNotNull null
            runCatching {
                MoneyEntry(
                    id = f[0].toLong(), cents = f[1].toLong(), kind = MoneyEntry.Kind.valueOf(f[2]),
                    description = f[3], createdAtMillis = f.getOrNull(4)?.toLongOrNull() ?: f[0].toLong(),
                    accountId = f.getOrNull(5)?.toLongOrNull(), categoryId = f.getOrNull(6)?.toLongOrNull(),
                    operationId = f.getOrNull(7)?.ifBlank { null } ?: f[0],
                    dateMillis = f.getOrNull(8)?.toLongOrNull() ?: (f.getOrNull(4)?.toLongOrNull() ?: f[0].toLong()),
                )
            }.getOrNull()
        }.sortedByDescending { it.createdAtMillis }

    fun add(cents: Long, kind: MoneyEntry.Kind, description: String, accountId: Long? = null, categoryId: Long? = null, operationId: String = UUID.randomUUID().toString(), dateMillis: Long = System.currentTimeMillis()): MoneyEntry {
        entries().firstOrNull { it.operationId == operationId }?.let { return it }
        val now = System.currentTimeMillis()
        val entry = MoneyEntry(now, cents, kind, defaultDescription(kind, description), now, accountId, categoryId, operationId = operationId, dateMillis = dateMillis)
        persist(listOf(entry) + entries()); return entry
    }

    fun get(id: Long) = entries().firstOrNull { it.id == id }

    fun update(id: Long, cents: Long, kind: MoneyEntry.Kind, description: String, accountId: Long? = null, categoryId: Long? = null) {
        val current = entries(); require(current.any { it.id == id }) { "Lançamento não encontrado" }
        persist(current.map { if (it.id == id) it.copy(cents = cents, kind = kind, description = defaultDescription(kind, description), accountId = accountId ?: it.accountId, categoryId = categoryId ?: it.categoryId) else it })
    }

    fun delete(id: Long) {
        val current = entries(); val remaining = current.filterNot { it.id == id }
        require(remaining.size != current.size) { "Lançamento não encontrado" }; persist(remaining)
    }

    fun clear() { preferences.edit().clear().commit() }

    private fun persist(items: List<MoneyEntry>) {
        val encoded = items.joinToString(RECORD_SEPARATOR) {
            listOf(it.id, it.cents, it.kind.name, it.description, it.createdAtMillis, it.accountId ?: "", it.categoryId ?: "", it.operationId, it.dateMillis).joinToString(FIELD_SEPARATOR)
        }
        check(preferences.edit().putString(KEY_ENTRIES, encoded).commit()) { "Não foi possível salvar o lançamento" }
    }

    private fun defaultDescription(kind: MoneyEntry.Kind, description: String) = description.ifBlank { if (kind == MoneyEntry.Kind.INCOME) "Entrada" else "Saída" }

    private companion object {
        const val FILE_NAME = "cupuwa_local_ledger"; const val KEY_ENTRIES = "entries.v1"
        const val RECORD_SEPARATOR = "\u001e"; const val FIELD_SEPARATOR = "\u001f"
    }
}
