import pytest

from host_execution_bridge import ApprovedHostExecutorBridge

NOW=2_000_000_000.0
APPROVAL='FOUNDER-ACTIVATION-SYN-R004-SOFTWARE-DELIVERY-V1-001'


def zero_cost(provider,target,capability):
    assert provider == 'GITHUB'
    assert target == 'github:jeffersonreisdejesus1-lgtm/reis-os-backend'
    assert capability == 'GITHUB_CREATE_OR_UPDATE_FILE'
    return 'ZERO-COST-PREFLIGHT:TEST'


def bridge(cost_verifier=zero_cost):
    return ApprovedHostExecutorBridge(
        founder_approval_ref=APPROVAL,
        allowed_providers=frozenset({'GITHUB','RENDER'}),
        allowed_target_prefixes=frozenset({'github:jeffersonreisdejesus1-lgtm/reis-os-backend','render:'}),
        allowed_capabilities=frozenset({'GITHUB_CREATE_BRANCH','GITHUB_CREATE_OR_UPDATE_FILE','GITHUB_OPEN_PR','GITHUB_UPDATE_PR','RENDER_TRIGGER_DEPLOY'}),
        zero_spend_verifier=cost_verifier,
        clock=lambda: NOW,
    )


def command(b=None):
    b=b or bridge()
    return b,b.prepare(
        request_id='syn-r004-host-canary-001',
        provider='GITHUB',
        target='github:jeffersonreisdejesus1-lgtm/reis-os-backend',
        capability='GITHUB_CREATE_OR_UPDATE_FILE',
        payload_ref='artifacts/SYN-R004-HOST-BRIDGE-CANARY-EFFECT-V1-001.md',
        lease_id='LEASE:SYN-R004-HOST-CANARY-001',
        expires_at_unix=NOW+600,
        max_effects=1,
    )


def test_prepare_is_deterministic_and_scope_bound():
    b,c1=command(); c2=b.prepare(
        request_id=c1.request_id,provider=c1.provider,target=c1.target,capability=c1.capability,
        payload_ref=c1.payload_ref,lease_id=c1.lease_id,expires_at_unix=c1.expires_at_unix,max_effects=1)
    assert c1 == c2
    assert c1.command_id.startswith('hostcmd:')
    assert c1.zero_spend_attestation_ref


def test_reconcile_requires_exact_prepared_command_and_evidence():
    b,c=command()
    r=b.reconcile(c,result_ref='github:commit:abc',external_receipt_ref='GitHub.create_file:abc')
    assert r.request_id == c.request_id
    assert r.status == 'COMMITTED'
    assert b.result_for_request(c.request_id) == r


def test_zero_spend_failure_blocks_prepare():
    b=bridge(lambda *_:'')
    with pytest.raises(RuntimeError, match='HOST_ZERO_SPEND_NOT_VERIFIED'):
        command(b)


def test_expired_lease_blocks_prepare():
    b=bridge()
    with pytest.raises(RuntimeError, match='HOST_LEASE_EXPIRED'):
        b.prepare(request_id='x',provider='GITHUB',target='github:jeffersonreisdejesus1-lgtm/reis-os-backend',capability='GITHUB_CREATE_OR_UPDATE_FILE',payload_ref='x',lease_id='L',expires_at_unix=NOW-1,max_effects=1)


def test_canary_requires_single_effect_lease():
    b=bridge()
    with pytest.raises(RuntimeError, match='HOST_CANARY_REQUIRES_SINGLE_EFFECT_LEASE'):
        b.prepare(request_id='x',provider='GITHUB',target='github:jeffersonreisdejesus1-lgtm/reis-os-backend',capability='GITHUB_CREATE_OR_UPDATE_FILE',payload_ref='x',lease_id='L',expires_at_unix=NOW+1,max_effects=2)


def test_merge_capability_is_not_in_initial_bridge_scope():
    b=bridge()
    with pytest.raises(RuntimeError, match='HOST_CAPABILITY_NOT_ALLOWED'):
        b.prepare(request_id='x',provider='GITHUB',target='github:jeffersonreisdejesus1-lgtm/reis-os-backend',capability='GITHUB_MERGE_PR',payload_ref='x',lease_id='L',expires_at_unix=NOW+1,max_effects=1)


def test_wrong_target_is_blocked():
    b=bridge()
    with pytest.raises(RuntimeError, match='HOST_TARGET_NOT_ALLOWED'):
        b.prepare(request_id='x',provider='GITHUB',target='github:other/repo',capability='GITHUB_CREATE_OR_UPDATE_FILE',payload_ref='x',lease_id='L',expires_at_unix=NOW+1,max_effects=1)
