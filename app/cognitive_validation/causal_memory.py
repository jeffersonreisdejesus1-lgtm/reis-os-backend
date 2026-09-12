from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class MemoryRecord:
    key: str
    value: float
    source_trace_id: str
    revision: int

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("memory key must be non-empty")
        if not self.source_trace_id:
            raise ValueError("memory source_trace_id must be non-empty")
        if self.revision < 1:
            raise ValueError("memory revision must be >= 1")


@dataclass(frozen=True)
class CausalMemoryStore:
    records: tuple[MemoryRecord, ...] = ()

    def remember(self, *, key: str, value: float, source_trace_id: str) -> "CausalMemoryStore":
        previous = self.get_record(key)
        revision = 1 if previous is None else previous.revision + 1
        record = MemoryRecord(
            key=key,
            value=value,
            source_trace_id=source_trace_id,
            revision=revision,
        )
        remaining = tuple(item for item in self.records if item.key != key)
        return replace(self, records=remaining + (record,))

    def get_record(self, key: str) -> MemoryRecord | None:
        for record in reversed(self.records):
            if record.key == key:
                return record
        return None

    def recall(self, key: str) -> float:
        record = self.get_record(key)
        return 0.0 if record is None else record.value

    def ablate(self, key: str) -> "CausalMemoryStore":
        return replace(self, records=tuple(item for item in self.records if item.key != key))


@dataclass(frozen=True)
class MemoryAugmentedDecision:
    stimulus: float
    memory_key: str
    memory_value: float
    score: float
    action: int
    memory_source_trace_id: str | None


class MemoryAugmentedDecisionEngine:
    @staticmethod
    def decide(
        *,
        stimulus: float,
        memory_key: str,
        memory: CausalMemoryStore,
    ) -> MemoryAugmentedDecision:
        record = memory.get_record(memory_key)
        memory_value = 0.0 if record is None else record.value
        score = stimulus + memory_value
        return MemoryAugmentedDecision(
            stimulus=stimulus,
            memory_key=memory_key,
            memory_value=memory_value,
            score=score,
            action=1 if score >= 0 else 0,
            memory_source_trace_id=None if record is None else record.source_trace_id,
        )
