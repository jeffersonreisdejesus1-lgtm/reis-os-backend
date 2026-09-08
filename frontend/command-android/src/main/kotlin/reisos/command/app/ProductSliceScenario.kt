package reisos.command.app

import reisos.command.adapters.adaptOcsProjection
import reisos.command.adapters.canRenderProgressPercent
import reisos.command.adapters.graphHasCanonicalRelationHold
import reisos.command.adapters.receiptIsVerified
import reisos.command.fixtures.SyntheticFixtures
import reisos.command.navigation.CommandRoute
import reisos.command.navigation.primaryNavigation
import reisos.command.ui_state.UiState

enum class ProductSemanticState {
    CURRENT,
    PARTIAL,
    STALE,
    UNKNOWN,
    HOLD,
    DENY,
    NOT_PROVEN,
}

data class ProductScreenSpec(
    val routeId: String,
    val title: String,
    val summary: String,
    val semanticState: ProductSemanticState,
    val evidence: List<String>,
)

data class ProductBoundary(
    val liveBackend: Boolean = false,
    val postgres: Boolean = false,
    val realAtlasL5: Boolean = false,
    val aiRuntime: Boolean = false,
    val kernelMutation: Boolean = false,
    val sourceClass: String = "LOCAL_PERSISTED_OFFLINE",
)

object ProductSliceScenario {
    val boundary = ProductBoundary()

    val screens: List<ProductScreenSpec> = listOf(
        ProductScreenSpec(
            "S0_HOME",
            "Situação atual",
            "Visão operacional local: mudanças, atenção, bloqueios e decisões.",
            ProductSemanticState.NOT_PROVEN,
            listOf("COMMAND_PROJECTION != SOURCE_OF_TRUTH", "persistence=LOCAL_DEVICE"),
        ),
        ProductScreenSpec(
            "S1_OPERATIONS",
            "Operações",
            "Operação ativa preserva progresso desconhecido; ausência de base não vira percentual.",
            ProductSemanticState.UNKNOWN,
            listOf("UNKNOWN != ZERO", "progress_basis=UNKNOWN"),
        ),
        ProductScreenSpec(
            "S2_OPERATION_DETAIL",
            "Detalhe da operação",
            "Receipt executado sem readback correspondente permanece não verificado.",
            ProductSemanticState.NOT_PROVEN,
            listOf("EXECUTED != VERIFIED", "readback_required"),
        ),
        ProductScreenSpec(
            "S3_OCS_DIRECTORY",
            "OCS",
            "Diretório local de OCS com identidade projetada e disponibilidade explícita.",
            ProductSemanticState.CURRENT,
            listOf("NAME_DOES_NOT_PROVE_IDENTITY", "projection_only"),
        ),
        ProductScreenSpec(
            "S4_OCS_DETAIL",
            "Detalhe da OCS",
            "Instância presente sem geração é renderizada como parcial, nunca como completa.",
            ProductSemanticState.PARTIAL,
            listOf("missing=generation", "PARTIAL != COMPLETE"),
        ),
        ProductScreenSpec(
            "S5_MAPS",
            "Mapa causal",
            "Relação desconhecida no grafo produz HOLD e não é promovida a causalidade conhecida.",
            ProductSemanticState.HOLD,
            listOf("UNKNOWN_EDGE_TYPE -> HOLD", "OWL_INFERENCE != GATE"),
        ),
        ProductScreenSpec(
            "S6_EVIDENCE",
            "Evidências",
            "Evidência sintética inválida permanece NOT_PROVEN e não assegura estado.",
            ProductSemanticState.NOT_PROVEN,
            listOf("MODEL_CONSENSUS != EVIDENCE", "validation=INVALID"),
        ),
        ProductScreenSpec(
            "S7_EVOLUTION",
            "Evolução",
            "A evolução exibida é projeção sintética e não altera estado canônico.",
            ProductSemanticState.NOT_PROVEN,
            listOf("UI_DOES_NOT_CREATE_AUTHORITY", "projection_only"),
        ),
        ProductScreenSpec(
            "S8_SYSTEM",
            "Sistema",
            "Componente disponível com telemetria stale continua stale; disponibilidade não implica atualidade.",
            ProductSemanticState.STALE,
            listOf("STALE != CURRENT", "availability != freshness"),
        ),
        ProductScreenSpec(
            "S9_CONVERSATION",
            "Conversa",
            "Contexto de navegação não transfere autoridade nem cria permissão operacional.",
            ProductSemanticState.DENY,
            listOf("HANDOFF_DOES_NOT_TRANSFER_AUTHORITY", "CAPABILITY != AUTHORITY"),
        ),
    )

    fun screen(routeId: String): ProductScreenSpec =
        screens.firstOrNull { it.routeId == routeId } ?: screens.first()

    fun primaryRouteIds(): List<String> = primaryNavigation.map(CommandRoute::id)

    fun invariantFailures(): List<String> = buildList {
        if (canRenderProgressPercent(SyntheticFixtures.operationActiveUnknownProgress)) {
            add("unknown_progress_rendered_as_percent")
        }
        if (receiptIsVerified(SyntheticFixtures.receiptWithoutReadback, null)) {
            add("executed_receipt_promoted_to_verified")
        }
        if (!graphHasCanonicalRelationHold(SyntheticFixtures.graphUnknownEdge)) {
            add("unknown_graph_relation_failed_to_hold")
        }
        if (adaptOcsProjection(SyntheticFixtures.ocsMissingGeneration) !is UiState.Partial<*>) {
            add("missing_generation_not_partial")
        }
        if (boundary.liveBackend || boundary.postgres || boundary.realAtlasL5 || boundary.aiRuntime || boundary.kernelMutation) {
            add("forbidden_runtime_boundary_open")
        }
    }
}
