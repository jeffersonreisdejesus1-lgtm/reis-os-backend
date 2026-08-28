from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field

from app.command.domain.observation import FreshnessState
from app.command.domain.projection import ProjectionContract


class AttentionClass(StrEnum):
    BLOCKER = "blocker"
    DECISION_PENDING = "decision_pending"
    CONFLICT = "conflict"
    RISK = "risk"
    STALE = "stale"
    SOURCE_UNAVAILABLE = "source_unavailable"
    SYNC_DEGRADED = "sync_degraded"
    AUTHORITY_MISSING = "authority_missing"
    ASSURANCE_PENDING = "assurance_pending"


class AttentionSeverity(StrEnum):
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"


class AttentionItemContract(BaseModel):
    model_config = ConfigDict(frozen=True)

    attention_id: UUID
    object_key: str = Field(min_length=1, max_length=255)
    projection_refs: tuple[UUID, ...] = Field(min_length=1)
    evidence_refs: tuple[UUID, ...] = Field(min_length=1)
    rule_id: str = Field(min_length=1, max_length=100)
    attention_class: AttentionClass
    reason: str = Field(min_length=1)
    severity: AttentionSeverity
    freshness_state: FreshnessState
    explanation: str = Field(min_length=1)
    derived_projection: bool = True


_SEVERITY_ORDER = {
    AttentionSeverity.P1: 0,
    AttentionSeverity.P2: 1,
    AttentionSeverity.P3: 2,
}


class AttentionEngine:
    def evaluate(
        self,
        projection: ProjectionContract,
    ) -> tuple[AttentionItemContract, ...]:
        items: list[AttentionItemContract] = []

        if projection.freshness_state is FreshnessState.CONFLICT:
            items.append(
                self._make_item(
                    projection,
                    "SOURCE_CONFLICT",
                    AttentionClass.CONFLICT,
                    AttentionSeverity.P1,
                    "Fontes em conflito",
                )
            )
        elif projection.freshness_state is FreshnessState.STALE:
            items.append(
                self._make_item(
                    projection,
                    "SOURCE_STALE",
                    AttentionClass.STALE,
                    AttentionSeverity.P2,
                    "Estado desatualizado",
                )
            )

        payload_rules = (
            (
                "BLOCKER_OPEN",
                "blocked",
                AttentionClass.BLOCKER,
                AttentionSeverity.P1,
                "Bloqueio material ativo",
            ),
            (
                "DECISION_PENDING",
                "decision_pending",
                AttentionClass.DECISION_PENDING,
                AttentionSeverity.P1,
                "Decisão pendente",
            ),
            (
                "SOURCE_UNAVAILABLE",
                "source_unavailable",
                AttentionClass.SOURCE_UNAVAILABLE,
                AttentionSeverity.P2,
                "Fonte indisponível",
            ),
            (
                "SYNC_DEGRADED",
                "sync_degraded",
                AttentionClass.SYNC_DEGRADED,
                AttentionSeverity.P2,
                "Sincronização degradada",
            ),
            (
                "RISK_OPEN",
                "risk",
                AttentionClass.RISK,
                AttentionSeverity.P2,
                "Risco relevante",
            ),
            (
                "AUTHORITY_MISSING",
                "authority_missing",
                AttentionClass.AUTHORITY_MISSING,
                AttentionSeverity.P3,
                "Autoridade ausente",
            ),
            (
                "ASSURANCE_PENDING",
                "assurance_pending",
                AttentionClass.ASSURANCE_PENDING,
                AttentionSeverity.P3,
                "Assurance pendente",
            ),
        )
        for rule_id, field, attention_class, severity, reason in payload_rules:
            if projection.projection_payload.get(field) is True:
                items.append(
                    self._make_item(
                        projection,
                        rule_id,
                        attention_class,
                        severity,
                        reason,
                    )
                )

        return tuple(
            sorted(
                items,
                key=lambda item: (_SEVERITY_ORDER[item.severity], item.rule_id),
            )
        )

    def _make_item(
        self,
        projection: ProjectionContract,
        rule_id: str,
        attention_class: AttentionClass,
        severity: AttentionSeverity,
        reason: str,
    ) -> AttentionItemContract:
        attention_id = uuid5(
            NAMESPACE_URL,
            f"{projection.projection_id}:{rule_id}",
        )
        return AttentionItemContract(
            attention_id=attention_id,
            object_key=projection.object_key,
            projection_refs=(projection.projection_id,),
            evidence_refs=projection.observation_refs,
            rule_id=rule_id,
            attention_class=attention_class,
            reason=reason,
            severity=severity,
            freshness_state=projection.freshness_state,
            explanation=(
                f"{reason}; derived from projection {projection.projection_id}"
            ),
        )
