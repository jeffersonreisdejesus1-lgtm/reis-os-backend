package reisos.command.app

data class OcsRosterEntry(
    val id: String,
    val name: String,
    val role: String,
    val state: ProductSemanticState,
)

data class OperationCardEntry(
    val id: String,
    val title: String,
    val owner: String,
    val state: ProductSemanticState,
    val progressLabel: String,
)

data class EvidenceCardEntry(
    val id: String,
    val objectRef: String,
    val validation: String,
    val state: ProductSemanticState,
)

data class SystemCardEntry(
    val id: String,
    val label: String,
    val availability: String,
    val freshness: ProductSemanticState,
)

object ProductDataCatalog {
    val ocsRoster: List<OcsRosterEntry> = listOf(
        OcsRosterEntry("OCS-NOESIS", "NÓESIS", "Orquestração e governança", ProductSemanticState.CURRENT),
        OcsRosterEntry("OCS-DEDALA", "DÉDALA", "Arquitetura, integração e assurance técnica", ProductSemanticState.CURRENT),
        OcsRosterEntry("OCS-SYNESIS", "SÝNESIS", "Assurance independente", ProductSemanticState.NOT_PROVEN),
        OcsRosterEntry("OCS-IRIS", "ÍRIS", "Experiência, interface e visualização", ProductSemanticState.PARTIAL),
        OcsRosterEntry("OCS-LYRA", "LYRA", "Marca e expressão institucional", ProductSemanticState.CURRENT),
        OcsRosterEntry("OCS-SOFIA", "SOFIA", "Implementação e engenharia", ProductSemanticState.CURRENT),
        OcsRosterEntry("OCS-METIS", "MÊTIS", "Autorização e gate", ProductSemanticState.HOLD),
        OcsRosterEntry("OCS-AGORA", "ÁGORA", "Backend, dados e eventos", ProductSemanticState.STALE),
        OcsRosterEntry("OCS-AURI", "AURI", "Proveniência e recuperação documental", ProductSemanticState.CURRENT),
        OcsRosterEntry("OCS-SYNERGEIA", "SYNERGEIA", "Integração e entrega externa", ProductSemanticState.UNKNOWN),
    )

    val operations: List<OperationCardEntry> = listOf(
        OperationCardEntry(
            id = "CMD-ANDROID-E2E-001",
            title = "Command Android product slice",
            owner = "DÉDALA",
            state = ProductSemanticState.UNKNOWN,
            progressLabel = "UNKNOWN — sem percentual sem base mensurável",
        ),
        OperationCardEntry(
            id = "CMD-IDENTITY-READBACK",
            title = "Identity and authority readback",
            owner = "NÓESIS",
            state = ProductSemanticState.NOT_PROVEN,
            progressLabel = "NOT_PROVEN — readback obrigatório",
        ),
        OperationCardEntry(
            id = "CMD-ATLAS-PROJECTION",
            title = "Atlas projection rehearsal",
            owner = "ÍRIS",
            state = ProductSemanticState.HOLD,
            progressLabel = "HOLD — relação causal desconhecida",
        ),
    )

    val evidence: List<EvidenceCardEntry> = listOf(
        EvidenceCardEntry("EVD-SYNTHETIC-HOME", "S0_HOME", "SYNTHETIC", ProductSemanticState.NOT_PROVEN),
        EvidenceCardEntry("EVD-RECEIPT-NO-READBACK", "S2_OPERATION_DETAIL", "UNVERIFIED", ProductSemanticState.NOT_PROVEN),
        EvidenceCardEntry("EVD-GRAPH-UNKNOWN", "S5_MAPS", "INVALID_FOR_CANONICAL_CAUSE", ProductSemanticState.HOLD),
        EvidenceCardEntry("EVD-SYSTEM-STALE", "S8_SYSTEM", "STALE", ProductSemanticState.STALE),
    )

    val systems: List<SystemCardEntry> = listOf(
        SystemCardEntry("KERNEL", "Kernel", "SYNTHETIC_AVAILABLE", ProductSemanticState.NOT_PROVEN),
        SystemCardEntry("HAZEL", "Hazel", "SYNTHETIC_AVAILABLE", ProductSemanticState.NOT_PROVEN),
        SystemCardEntry("MISSION_JOURNAL", "Mission Journal", "SYNTHETIC_AVAILABLE", ProductSemanticState.NOT_PROVEN),
        SystemCardEntry("COMMAND", "Command", "AVAILABLE", ProductSemanticState.STALE),
        SystemCardEntry("ATLAS", "Atlas projection", "SYNTHETIC_ONLY", ProductSemanticState.HOLD),
    )

    val homeFacts: List<String> = listOf(
        "10 OCS catalogadas no slice sintético",
        "3 operações longitudinais de demonstração",
        "1 relação causal deliberadamente mantida em HOLD",
        "0 caminhos de mutação do Kernel",
    )

    fun itemsFor(routeId: String): List<String> = when (routeId) {
        "S0_HOME" -> homeFacts
        "S1_OPERATIONS" -> operations.map { "${it.id} · ${it.title} · ${it.state} · ${it.progressLabel}" }
        "S2_OPERATION_DETAIL" -> listOf(
            "receipt=EXECUTED",
            "readback=MISSING",
            "derived_state=NOT_PROVEN",
            "rule=EXECUTED != VERIFIED",
        )
        "S3_OCS_DIRECTORY" -> ocsRoster.map { "${it.name} · ${it.role} · ${it.state}" }
        "S4_OCS_DETAIL" -> listOf(
            "ÍRIS · instance=fixture-instance-iris",
            "generation=MISSING",
            "derived_state=PARTIAL",
            "rule=PARTIAL != COMPLETE",
        )
        "S5_MAPS" -> listOf(
            "graph=fixture-graph",
            "edge=UNKNOWN_EDGE_TYPE",
            "derived_state=HOLD",
            "rule=unknown relation cannot become canonical cause",
        )
        "S6_EVIDENCE" -> evidence.map { "${it.id} · ${it.objectRef} · ${it.validation} · ${it.state}" }
        "S7_EVOLUTION" -> listOf(
            "projection-only evolution timeline",
            "no canonical writes",
            "no promotion authority",
            "UI_DOES_NOT_CREATE_AUTHORITY",
        )
        "S8_SYSTEM" -> systems.map { "${it.label} · ${it.availability} · freshness=${it.freshness}" }
        "S9_CONVERSATION" -> listOf(
            "context can be carried",
            "authority cannot be transferred by navigation",
            "handoff does not transfer authority",
            "capability does not imply authority",
        )
        else -> emptyList()
    }
}
