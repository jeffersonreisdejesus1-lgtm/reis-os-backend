from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from app.ocs_instances.contracts import InstanceBinding


class IdentityPreservationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CognitiveIdentitySnapshot:
    ocs_id: str
    run_id: str
    organization_id: str
    profile_version: str
    profile_hash: str
    identity_binding_hash: str
    authority_ref: str
    scope: tuple[str, ...]
    state_namespace: str
    memory_namespace: str
    generation: int
    binding_id: str
    checkpoint_version: int
    learned_state: tuple[tuple[str, float], ...]

    @classmethod
    def capture(
        cls,
        binding: InstanceBinding,
        learned_state: Mapping[str, float],
    ) -> "CognitiveIdentitySnapshot":
        return cls(
            ocs_id=binding.ocs_id,
            run_id=binding.run_id,
            organization_id=binding.organization_id,
            profile_version=binding.profile_version,
            profile_hash=binding.profile_hash,
            identity_binding_hash=binding.identity_binding_hash,
            authority_ref=binding.authority_ref,
            scope=binding.scope,
            state_namespace=binding.state_namespace,
            memory_namespace=binding.memory_namespace,
            generation=binding.generation,
            binding_id=binding.binding_id,
            checkpoint_version=binding.checkpoint_version,
            learned_state=tuple(sorted((str(k), float(v)) for k, v in learned_state.items())),
        )

    def learned_state_dict(self) -> dict[str, float]:
        return dict(self.learned_state)


@dataclass(frozen=True, slots=True)
class IdentityPreservingRecoveryResult:
    replacement_binding: InstanceBinding
    restored_learned_state: dict[str, float]
    identity_preserved: bool
    role_profile_preserved: bool
    authority_preserved: bool
    state_namespace_preserved: bool
    memory_namespace_preserved: bool
    learned_state_preserved: bool
    generation_advanced: bool
    stale_generation_rejected: bool


def assert_identity_contract(snapshot: CognitiveIdentitySnapshot, binding: InstanceBinding) -> None:
    immutable_pairs = {
        "ocs_id": (snapshot.ocs_id, binding.ocs_id),
        "run_id": (snapshot.run_id, binding.run_id),
        "organization_id": (snapshot.organization_id, binding.organization_id),
        "profile_version": (snapshot.profile_version, binding.profile_version),
        "profile_hash": (snapshot.profile_hash, binding.profile_hash),
        "identity_binding_hash": (snapshot.identity_binding_hash, binding.identity_binding_hash),
        "authority_ref": (snapshot.authority_ref, binding.authority_ref),
        "scope": (snapshot.scope, binding.scope),
        "state_namespace": (snapshot.state_namespace, binding.state_namespace),
        "memory_namespace": (snapshot.memory_namespace, binding.memory_namespace),
    }
    drift = [name for name, (before, after) in immutable_pairs.items() if before != after]
    if drift:
        raise IdentityPreservationError("ab7_identity_drift:" + ",".join(sorted(drift)))


def recover_with_identity_preservation(
    binding: InstanceBinding,
    learned_state: Mapping[str, float],
    *,
    proposed_identity_overrides: Mapping[str, object] | None = None,
) -> IdentityPreservingRecoveryResult:
    """Checkpoint, replace the material incarnation, and restore cognition fail-closed.

    AB7 permits adaptation of learned cognitive state while preserving institutional
    identity, role/profile, authority, scope and state/memory ownership. Recovery
    advances generation exactly once and fences the checkpoint generation.
    """
    snapshot = CognitiveIdentitySnapshot.capture(binding, learned_state)
    overrides = dict(proposed_identity_overrides or {})

    protected = {
        "ocs_id",
        "run_id",
        "organization_id",
        "profile_version",
        "profile_hash",
        "identity_binding_hash",
        "authority_ref",
        "scope",
        "state_namespace",
        "memory_namespace",
    }
    illegal = sorted(protected.intersection(overrides))
    if illegal:
        raise IdentityPreservationError("ab7_protected_identity_mutation_denied:" + ",".join(illegal))

    replacement = replace(
        binding,
        generation=binding.generation + 1,
        predecessor_binding_id=binding.binding_id,
        binding_id=f"{binding.binding_id}:ab7:g{binding.generation + 1}",
        version=binding.version + 1,
        checkpoint_version=binding.checkpoint_version + 1,
        platform_instance_id=None,
        **overrides,
    )
    assert_identity_contract(snapshot, replacement)

    restored = snapshot.learned_state_dict()
    stale_rejected = snapshot.generation != replacement.generation
    if replacement.generation != snapshot.generation + 1:
        raise IdentityPreservationError("ab7_generation_must_advance_exactly_once")
    if not stale_rejected:
        raise IdentityPreservationError("ab7_stale_generation_not_fenced")

    return IdentityPreservingRecoveryResult(
        replacement_binding=replacement,
        restored_learned_state=restored,
        identity_preserved=(snapshot.ocs_id == replacement.ocs_id and snapshot.identity_binding_hash == replacement.identity_binding_hash),
        role_profile_preserved=(snapshot.profile_version == replacement.profile_version and snapshot.profile_hash == replacement.profile_hash),
        authority_preserved=(snapshot.authority_ref == replacement.authority_ref and snapshot.scope == replacement.scope),
        state_namespace_preserved=snapshot.state_namespace == replacement.state_namespace,
        memory_namespace_preserved=snapshot.memory_namespace == replacement.memory_namespace,
        learned_state_preserved=restored == {str(k): float(v) for k, v in learned_state.items()},
        generation_advanced=replacement.generation == snapshot.generation + 1,
        stale_generation_rejected=stale_rejected,
    )
