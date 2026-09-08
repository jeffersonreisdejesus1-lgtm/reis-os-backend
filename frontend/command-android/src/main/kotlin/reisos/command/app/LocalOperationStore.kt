package reisos.command.app

import android.content.Context

data class PersistedOperation(
    val id: String,
    val title: String,
    val owner: String,
    val state: ProductSemanticState,
    val progressLabel: String,
    val lastAction: String,
    val revision: Long,
)

class LocalOperationStore(context: Context) {
    private val preferences = context.getSharedPreferences(FILE_NAME, Context.MODE_PRIVATE)

    fun operations(): List<PersistedOperation> =
        readRecords().ifEmpty {
            val initial = defaultOperations()
            writeRecords(initial)
            initial
        }

    fun operation(id: String): PersistedOperation? =
        operations().firstOrNull { it.id == id }

    fun select(id: String) {
        preferences.edit().putString(KEY_SELECTED, id).apply()
    }

    fun selectedId(): String? = preferences.getString(KEY_SELECTED, null)

    fun updateAction(id: String, action: String): PersistedOperation? {
        val updated = operations().map {
            if (it.id == id) it.copy(lastAction = action, revision = it.revision + 1) else it
        }
        writeRecords(updated)
        return updated.firstOrNull { it.id == id }
    }

    private fun readRecords(): List<PersistedOperation> {
        val raw = preferences.getString(KEY_RECORDS, null) ?: return emptyList()
        return raw.split(RECORD_SEPARATOR).filter { it.isNotBlank() }.mapNotNull { row ->
            val fields = row.split(FIELD_SEPARATOR)
            if (fields.size != 7) return@mapNotNull null
            runCatching {
                PersistedOperation(
                    id = fields[0],
                    title = fields[1],
                    owner = fields[2],
                    state = ProductSemanticState.valueOf(fields[3]),
                    progressLabel = fields[4],
                    lastAction = fields[5],
                    revision = fields[6].toLong(),
                )
            }.getOrNull()
        }
    }

    private fun writeRecords(records: List<PersistedOperation>) {
        val encoded = records.joinToString(RECORD_SEPARATOR) { record ->
            listOf(record.id, record.title, record.owner, record.state.name,
                record.progressLabel, record.lastAction, record.revision.toString())
                .joinToString(FIELD_SEPARATOR)
        }
        preferences.edit().putString(KEY_RECORDS, encoded).apply()
    }

    private fun defaultOperations() = listOf(
        PersistedOperation(
            id = "CMD-ANDROID-E2E-001",
            title = "Command Android product slice",
            owner = "SOFIA",
            state = ProductSemanticState.CURRENT,
            progressLabel = "LOCAL — estado persistido neste dispositivo",
            lastAction = "Operação criada localmente",
            revision = 1L,
        ),
        PersistedOperation(
            id = "CMD-IDENTITY-READBACK",
            title = "Identity and authority readback",
            owner = "NÓESIS",
            state = ProductSemanticState.NOT_PROVEN,
            progressLabel = "NOT_PROVEN — readback obrigatório",
            lastAction = "Aguardando evidência",
            revision = 1L,
        ),
        PersistedOperation(
            id = "CMD-ATLAS-PROJECTION",
            title = "Atlas projection rehearsal",
            owner = "ÍRIS",
            state = ProductSemanticState.HOLD,
            progressLabel = "HOLD — relação causal desconhecida",
            lastAction = "Mantida em HOLD",
            revision = 1L,
        ),
    )

    private companion object {
        const val FILE_NAME = "command_local_operations"
        const val KEY_RECORDS = "records.v1"
        const val KEY_SELECTED = "selected.v1"
        const val RECORD_SEPARATOR = "\u001E"
        const val FIELD_SEPARATOR = "\u001F"
    }
}
