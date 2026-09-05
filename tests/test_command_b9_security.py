from __future__ import annotations

from dataclasses import replace

from app.command.security import (
    CommandSecurityDecision,
    CommandSecurityGuard,
    CommandSecurityRequest,
    command_security_posture,
)
from app.memberships.domain.enums import MembershipRole
from app.profile_bindings.profiles import PROFILES


def _request(
    *,
    role: MembershipRole = MembershipRole.OWNER,
    founder_sensitive: bool = False,
) -> CommandSecurityRequest:
    return CommandSecurityRequest(
        request_id="request-b9-001",
        organization_id="reis-os-org",
        expected_organization_id="reis-os-org",
        role=role,
        ocs_id="ÁGORA",
        namespace=PROFILES["ÁGORA"].state_namespace,
        idempotency_key="idem-b9-001",
        payload={"operation": "inspect", "secret": "do-not-log"},
        founder_sensitive=founder_sensitive,
    )


def test_b9_valid_request_is_allowed_without_execution() -> None:
    readback = CommandSecurityGuard().evaluate(_request())

    assert readback.decision is CommandSecurityDecision.ALLOW
    assert readback.mutation_count == 0
    assert readback.idempotent_replay is False


def test_b9_organization_and_role_denials_have_zero_mutations() -> None:
    guard = CommandSecurityGuard()

    wrong_org = guard.evaluate(
        replace(_request(), organization_id="foreign-organization")
    )
    wrong_role = guard.evaluate(_request(role=MembershipRole.MEMBER))

    assert wrong_org.decision is CommandSecurityDecision.DENY
    assert wrong_org.mutation_count == 0
    assert wrong_role.decision is CommandSecurityDecision.DENY
    assert wrong_role.mutation_count == 0


def test_b9_founder_sensitive_request_requires_owner() -> None:
    readback = CommandSecurityGuard().evaluate(
        _request(role=MembershipRole.ADMIN, founder_sensitive=True)
    )

    assert readback.decision is CommandSecurityDecision.DENY
    assert readback.reason == "command_security_founder_role_required"
    assert readback.mutation_count == 0


def test_b9_cross_ocs_namespace_is_rejected() -> None:
    request = replace(
        _request(),
        namespace=PROFILES["NÓESIS"].state_namespace,
    )

    readback = CommandSecurityGuard().evaluate(request)

    assert readback.decision is CommandSecurityDecision.DENY
    assert readback.reason == "command_security_namespace_mismatch"
    assert readback.mutation_count == 0


def test_b9_idempotent_replay_and_conflict_are_distinguished() -> None:
    guard = CommandSecurityGuard()
    request = _request()

    first = guard.evaluate(request)
    replay = guard.evaluate(request)
    conflict = guard.evaluate(
        replace(request, payload={"operation": "different"})
    )

    assert first.decision is CommandSecurityDecision.ALLOW
    assert replay.decision is CommandSecurityDecision.ALLOW
    assert replay.idempotent_replay is True
    assert replay.mutation_count == 0
    assert conflict.decision is CommandSecurityDecision.DENY
    assert conflict.reason == "command_security_idempotency_conflict"
    assert conflict.mutation_count == 0


def test_b9_audit_redacts_secrets() -> None:
    request = replace(
        _request(),
        payload={
            "password": "one",
            "nested": {"access_token": "two", "safe": "visible"},
        },
    )

    readback = CommandSecurityGuard().evaluate(request)

    assert readback.audit["payload"]["password"] == "[REDACTED]"
    assert readback.audit["payload"]["nested"]["access_token"] == "[REDACTED]"
    assert readback.audit["payload"]["nested"]["safe"] == "visible"
    assert "idem-b9-001" not in str(readback.audit)


def test_b9_posture_does_not_fabricate_device_session_support() -> None:
    posture = command_security_posture()

    assert posture["device_session_binding"] == "not_materialized"
    assert posture["authority_bypass"] == "forbidden"
    assert posture["cross_ocs_write"] == "forbidden"
