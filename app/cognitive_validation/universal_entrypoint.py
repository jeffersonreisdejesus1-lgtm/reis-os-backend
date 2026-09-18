from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .integrated_architecture import IntegratedCognitiveArchitecture


class CognitiveEntrypointError(RuntimeError):
    """Fail-closed error raised when canonical cognition cannot be established."""


@dataclass(frozen=True, slots=True)
class CognitiveMissionContext:
    mission_id: str
    ocs_id: str
    ocs_instance_id: str
    generation: int
    intent: str
    state_revision: str | None = None

    def validate(self) -> None:
        required = {
            "mission_id": self.mission_id,
            "ocs_id": self.ocs_id,
            "ocs_instance_id": self.ocs_instance_id,
            "intent": self.intent,
        }
        missing = tuple(name for name, value in required.items() if not value.strip())
        if missing:
            raise CognitiveEntrypointError(
                f"cognitive_entry_context_invalid:missing={','.join(missing)}"
            )
        if self.generation < 0:
            raise CognitiveEntrypointError("cognitive_entry_context_invalid:generation")


@dataclass(frozen=True, slots=True)
class CognitiveProposal:
    mission_id: str
    ocs_id: str
    ocs_instance_id: str
    generation: int
    brain_version: str
    brain_state_revision: str | None
    integrated_score: float
    cognitive_path_used: bool
    authority_granted: bool = False
    effects_permitted: bool = False


@runtime_checkable
class CognitiveBrain(Protocol):
    version: str

    def evaluate(self, context: CognitiveMissionContext) -> float:
        """Return a deterministic integrated-cognition score for the mission."""


class ValidatedArtificialBrain:
    """COI1 adapter over the already-qualified AB9 integrated architecture.

    This class does not grant authority and does not execute effects. It only
    establishes that the canonical cognitive path is intact and available.
    """

    version = "AB0-AB13/canonical"

    def __init__(self) -> None:
        self._architecture = IntegratedCognitiveArchitecture()

    def evaluate(self, context: CognitiveMissionContext) -> float:
        del context  # COI1 validates routing, not mission-specific planning yet.
        outcome = self._architecture.assert_integrated()
        if not outcome.success or outcome.score != 1.0:
            raise CognitiveEntrypointError("canonical_brain_not_integrated")
        return outcome.score


class UniversalCognitiveEntrypoint:
    """Canonical mission ingress for REIS OS cognition.

    COI1 scope:
    - requires mission/OCS/generation context;
    - routes cognition through a canonical brain interface;
    - fails closed when cognition is absent, invalid, or degraded;
    - never turns cognitive output into authority or execution permission.

    Receipt issuance, bootstrap binding and hard adapter anti-bypass are owned
    by later COI gates and intentionally do not live here.
    """

    def __init__(self, brain: CognitiveBrain | None = None) -> None:
        self._brain = brain if brain is not None else ValidatedArtificialBrain()

    def enter(self, context: CognitiveMissionContext) -> CognitiveProposal:
        context.validate()

        brain = self._brain
        if brain is None or not isinstance(brain, CognitiveBrain):
            raise CognitiveEntrypointError("brain_unavailable")

        try:
            score = brain.evaluate(context)
        except CognitiveEntrypointError:
            raise
        except Exception as exc:
            raise CognitiveEntrypointError("brain_unavailable") from exc

        if not isinstance(score, (int, float)) or isinstance(score, bool):
            raise CognitiveEntrypointError("invalid_cognitive_result")
        score = float(score)
        if score != 1.0:
            raise CognitiveEntrypointError("cognitive_path_not_intact")

        return CognitiveProposal(
            mission_id=context.mission_id,
            ocs_id=context.ocs_id,
            ocs_instance_id=context.ocs_instance_id,
            generation=context.generation,
            brain_version=brain.version,
            brain_state_revision=context.state_revision,
            integrated_score=score,
            cognitive_path_used=True,
            authority_granted=False,
            effects_permitted=False,
        )
