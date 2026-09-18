from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

OCS_IDS = (
    "NOESIS",
    "DEDALA",
    "SYNESIS",
    "AGORA",
    "AURI",
    "SOFIA",
    "IRIS",
    "LYRA",
    "METIS",
    "SYNERGEIA",
    "THEMIS",
)


@dataclass
class CognitiveActor:
    ocs_id: str
    logical_runtime_id: str
    instance_id: str
    generation: int = 1
    alive: bool = True
    local_memory: dict[str, int] = field(default_factory=dict)

    def process(self, task_family: str, signal: int) -> int:
        if not self.alive:
            raise RuntimeError("ACTOR_NOT_OPERATIONAL")
        self.local_memory[task_family] = self.local_memory.get(task_family, 0) + 1
        specialization = (OCS_IDS.index(self.ocs_id) % 3) + 1
        return signal + specialization


@dataclass(frozen=True)
class Message:
    sender: str
    receiver: str
    task_family: str
    value: int
    ordinal: int


class GovernedBus:
    def __init__(self) -> None:
        self.trace: list[Message] = []

    def send(self, *, sender: CognitiveActor, receiver: CognitiveActor, task_family: str, value: int) -> Message:
        if sender.ocs_id == receiver.ocs_id:
            raise RuntimeError("SELF_ROUTE_FORBIDDEN")
        if not sender.alive or not receiver.alive:
            raise RuntimeError("ROUTE_ENDPOINT_NOT_OPERATIONAL")
        message = Message(sender.ocs_id, receiver.ocs_id, task_family, value, len(self.trace) + 1)
        self.trace.append(message)
        return message


@dataclass(frozen=True)
class DistributedCognitionResult:
    task_family: str
    active_actors: tuple[str, ...]
    contribution_by_actor: dict[str, int]
    aggregate_score: int
    trace: tuple[Message, ...]
    hidden_central_mind: bool


class DistributedIntegratedCognition:
    def __init__(self) -> None:
        self.actors = {
            ocs_id: CognitiveActor(
                ocs_id=ocs_id,
                logical_runtime_id=f"runtime::{ocs_id.lower()}",
                instance_id=f"instance::{ocs_id.lower()}::g1",
            )
            for ocs_id in OCS_IDS
        }
        self.bus = GovernedBus()

    def kill(self, ocs_id: str) -> None:
        self.actors[ocs_id].alive = False

    def revive(self, ocs_id: str) -> None:
        actor = self.actors[ocs_id]
        actor.generation += 1
        actor.instance_id = f"instance::{ocs_id.lower()}::g{actor.generation}"
        actor.alive = True

    def run(self, task_family: str, *, ablate: Iterable[str] = ()) -> DistributedCognitionResult:
        ablated = frozenset(ablate)
        contributions: dict[str, int] = {}
        active = [actor for actor in self.actors.values() if actor.alive and actor.ocs_id not in ablated]
        if len(active) < 2:
            raise RuntimeError("INSUFFICIENT_DISTRIBUTED_ACTORS")

        signal = len(task_family)
        for index, actor in enumerate(active):
            local = actor.process(task_family, signal + index)
            contributions[actor.ocs_id] = local
            if index:
                self.bus.send(
                    sender=active[index - 1],
                    receiver=actor,
                    task_family=task_family,
                    value=local,
                )

        return DistributedCognitionResult(
            task_family=task_family,
            active_actors=tuple(actor.ocs_id for actor in active),
            contribution_by_actor=contributions,
            aggregate_score=sum(contributions.values()),
            trace=tuple(self.bus.trace),
            hidden_central_mind=False,
        )

    def memory_snapshot(self) -> dict[str, dict[str, int]]:
        return {ocs_id: dict(actor.local_memory) for ocs_id, actor in self.actors.items()}
