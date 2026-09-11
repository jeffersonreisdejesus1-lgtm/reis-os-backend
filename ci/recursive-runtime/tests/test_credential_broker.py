import pytest

from authority_gateway import AuthorityGateway, AuthorityGatewayPolicy
from credential_broker import CredentialBroker, ProviderIsolationAttestation
from orchestrator_effect_bridge import OrchestratorEffectAuthorization

NOW = 2_000_000_000.0
MISSION = "REIS-AI-MUTATION-ISOLATION-V1-001"
RUN = "ORCH-RUN-AI-MUTATION-ISOLATION-V1-001"
TARGET = "github:jeffersonreisdejesus1-lgtm/reis-os-backend"
CAP = "GITHUB_CREATE_OR_UPDATE_FILE"
PATH = "ci/recursive-runtime/credential_broker.py"
APPROVAL = "FOUNDER-AUTH-AI-MUTATION-ISOLATION-V1-001"
HOST = "approved-host-executor:reis-os-v1"


def prepared():
    policy = AuthorityGatewayPolicy(
        policy_id="AI-MUTATION-ISOLATION-V1",
        mission_id=MISSION,
        orchestrator_run_id=RUN,
        mission_stage="IMPLEMENTATION",
        canonical_identity="SOFIA",
        target=TARGET,
        allowed_capabilities=frozenset({CAP}),
        allowed_payload_paths=frozenset({PATH}),
        founder_approval_ref=APPROVAL,
    )
    auth = OrchestratorEffectAuthorization(
        authorization_id="AUTHZ:AI-ISOLATION:001",
        mission_id=MISSION,
        orchestrator_run_id=RUN,
        mission_stage="IMPLEMENTATION",
        actor_id="actor:sofia:001",
        canonical_identity="SOFIA",
        authority_ref="AUTH:SOFIA:AI-ISOLATION",
        mission_binding=MISSION,
        delegation_ref="DELEGATION:NOESIS:SOFIA:AI-ISOLATION",
        target=TARGET,
        capability=CAP,
        payload_ref=PATH,
        founder_approval_ref=APPROVAL,
        generation=1,
        fencing_epoch=1,
        request_id="effect:ai-isolation:001",
        evidence_parent="SYNESIS-ARCH-ASSURANCE-AI-MUTATION-ISOLATION-V1-001",
        issued_at_unix=NOW - 5,
        expires_at_unix=NOW + 300,
    )
    return AuthorityGateway(policy, clock=lambda: NOW).authorize(auth)


def broker():
    return CredentialBroker(approved_host_executors=frozenset({HOST}), clock=lambda: NOW)


def attest(b):
    return b.register_isolation_attestation(ProviderIsolationAttestation(
        provider="GITHUB",
        credential_owner=HOST,
        direct_ai_write_access_removed=True,
        alternate_write_paths_reviewed=True,
        evidence_ref="provider-isolation-evidence:github:001",
        observed_at_unix=NOW - 1,
        valid_until_unix=NOW + 600,
    ))


def test_ai_raw_credential_request_is_always_denied_and_audited():
    b = broker()
    with pytest.raises(RuntimeError, match="RAW_CREDENTIAL_EXPORT_FORBIDDEN"):
        b.request_raw_credential(actor_class="OCS", actor_id="SOFIA", provider="GITHUB")
    events = b.audit_events()
    assert events[-1].decision == "DENY"
    assert events[-1].reason == "RAW_CREDENTIAL_EXPORT_FORBIDDEN"


def test_no_provider_isolation_attestation_means_no_grant():
    b = broker()
    with pytest.raises(RuntimeError, match="PROVIDER_ISOLATION_NOT_ATTESTED"):
        b.issue_grant(actor_class="OCS", actor_id="SOFIA", provider="GITHUB",
                      host_executor_id=HOST, prepared=prepared())
    assert b.audit_events()[-1].decision == "DENY"


def test_attestation_refuses_provider_when_direct_ai_write_still_present():
    b = broker()
    with pytest.raises(RuntimeError, match="DIRECT_AI_WRITE_ACCESS_STILL_PRESENT"):
        b.register_isolation_attestation(ProviderIsolationAttestation(
            provider="GITHUB", credential_owner=HOST,
            direct_ai_write_access_removed=False,
            alternate_write_paths_reviewed=True,
            evidence_ref="evidence", observed_at_unix=NOW - 1,
            valid_until_unix=NOW + 600,
        ))


def test_valid_governed_path_issues_opaque_one_shot_grant():
    b = broker(); attest(b)
    grant = b.issue_grant(actor_class="OCS", actor_id="SOFIA", provider="GITHUB",
                          host_executor_id=HOST, prepared=prepared())
    assert grant.capability == CAP
    assert grant.target == TARGET
    assert not hasattr(grant, "credential")
    consumed = b.consume_grant(grant=grant, host_executor_id=HOST)
    assert consumed.grant_id == grant.grant_id
    with pytest.raises(RuntimeError, match="GRANT_REPLAY_DENIED"):
        b.consume_grant(grant=grant, host_executor_id=HOST)


def test_wrong_host_cannot_consume_grant():
    b = broker(); attest(b)
    grant = b.issue_grant(actor_class="OCS", actor_id="SOFIA", provider="GITHUB",
                          host_executor_id=HOST, prepared=prepared())
    with pytest.raises(RuntimeError, match="HOST_EXECUTOR_MISMATCH"):
        b.consume_grant(grant=grant, host_executor_id="ai-session:chatgpt")


def test_unreviewed_alternate_write_paths_fail_closed():
    b = broker()
    with pytest.raises(RuntimeError, match="ALTERNATE_WRITE_PATHS_NOT_REVIEWED"):
        b.register_isolation_attestation(ProviderIsolationAttestation(
            provider="GITHUB", credential_owner=HOST,
            direct_ai_write_access_removed=True,
            alternate_write_paths_reviewed=False,
            evidence_ref="evidence", observed_at_unix=NOW - 1,
            valid_until_unix=NOW + 600,
        ))
