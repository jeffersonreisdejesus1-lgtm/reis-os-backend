import pytest

from host_execution_bridge import ApprovedHostExecutorBridge
from production_effects import (
    ActivationLease,
    EffectRequest,
    GitHubProductionAdapter,
    ProductionAuthorizationPolicy,
    ProductionEffectGateway,
    VerifiedCostDecision,
)
from ocs_operationalization import OCSRuntimeEnforcer
from recursive_runtime.contracts.model import *
from recursive_runtime.repositories.state import *
from recursive_runtime.services.core import *

NOW=2_000_000_000.0
APPROVAL='FOUNDER-ACTIVATION-SYN-R004-SOFTWARE-DELIVERY-V1-001'
TARGET='github:jeffersonreisdejesus1-lgtm/reis-os-backend'
CAP='GITHUB_CREATE_OR_UPDATE_FILE'
PAYLOAD='artifacts/SYN-R004-HOST-BRIDGE-CANARY-EFFECT-V1-001.md'
REQ_ID='syn-r004-host-canary-001'


def build(tmp_path):
    states=StateRepository(); receipts=ReceiptRepository()
    actor=ActorState(actor_id='a',identity_id='NOESIS',session_binding='S1',mission_binding='M1',state_namespace='ns:a',authority=AuthorityGrant('AUTH:1',frozenset({'read','write','delegate'})),capability=CapabilityBinding('CAP:1',frozenset({CAP}),frozenset({'tool:a'})),budget_ref='B1',provider_id='provider-canonical',trace_id='T1',span_id='span:a',generation=1,fencing_epoch=1,cancellation_policy_ref='C1')
    states.add(actor); trace=TraceService(receipts); trace.emit('SPAN_OPEN',actor,'ROOT')
    journal=DurableJournalRepository(tmp_path/'effects.jsonl')
    host=ApprovedHostExecutorBridge(
        founder_approval_ref=APPROVAL,
        allowed_providers=frozenset({'GITHUB'}),
        allowed_target_prefixes=frozenset({TARGET}),
        allowed_capabilities=frozenset({CAP}),
        zero_spend_verifier=lambda p,t,c:'ZERO-COST-PREFLIGHT:HOST-CANARY-001',
        clock=lambda:NOW,
    )
    lease=ActivationLease('LEASE:SYN-R004-HOST-CANARY-001','PRODUCTION',frozenset({TARGET}),frozenset({CAP}),APPROVAL,True,1,NOW+600)
    policy=ProductionAuthorizationPolicy('SYN-R004-GITHUB-RENDER-ZERO-SPEND-V1',frozenset({'NOESIS'}),frozenset({TARGET}),frozenset({CAP}),APPROVAL,True,False,True)
    request=EffectRequest(REQ_ID,'a',TARGET,CAP,PAYLOAD,'AUTH:1','M1',1,1)

    def host_executor(r):
        cmd=host.prepare(request_id=r.request_id,provider='GITHUB',target=r.target,capability=r.capability,payload_ref=r.payload_ref,lease_id=lease.lease_id,expires_at_unix=lease.expires_at_unix,max_effects=lease.max_effects)
        raise RuntimeError('HOST_EXECUTION_PENDING:'+cmd.command_id)

    def reconcile(r):
        result=host.result_for_request(r.request_id)
        return result.result_ref if result is not None else None

    gateway=ProductionEffectGateway(
        states,trace,OCSRuntimeEnforcer(),GitHubProductionAdapter(host_executor),lease,policy,
        approval_verifier=lambda p,l,a,r: p.founder_approval_ref==APPROVAL and l.founder_approval_ref==APPROVAL,
        cost_preflight=lambda r: VerifiedCostDecision(r.request_id,r.target,r.capability,0.0,False,'ZERO-COST-PREFLIGHT:GATEWAY-001',NOW+300),
        clock=lambda:NOW,effect_journal=journal,provider_reconciler=reconcile,
    )
    return gateway,host,request,journal,receipts


def test_gateway_persists_intent_then_host_executes_then_gateway_reconciles(tmp_path):
    gateway,host,request,journal,receipts=build(tmp_path)

    with pytest.raises(RuntimeError, match='HOST_EXECUTION_PENDING:'):
        gateway.execute(request)

    rows=journal.all()
    intents=[r for r in rows if r['kind']=='PRODUCTION_EFFECT_INTENT']
    commits=[r for r in rows if r['kind']=='PRODUCTION_EFFECT_COMMIT']
    assert len(intents)==1 and len(commits)==0

    command=next(iter(host._commands.values()))
    host.reconcile(command,result_ref='github:commit:REAL_CANARY_SHA',external_receipt_ref='GitHub.create_file:REAL_CANARY_SHA')

    receipt=gateway.execute(request)
    assert receipt.status=='COMMITTED'
    assert receipt.result_ref=='github:commit:REAL_CANARY_SHA'
    rows=journal.all()
    commits=[r for r in rows if r['kind']=='PRODUCTION_EFFECT_COMMIT']
    assert len(commits)==1


def test_unknown_host_outcome_holds_without_blind_retry(tmp_path):
    gateway,host,request,journal,_=build(tmp_path)
    with pytest.raises(RuntimeError, match='HOST_EXECUTION_PENDING:'):
        gateway.execute(request)
    with pytest.raises(RuntimeError, match='EFFECT_OUTCOME_UNKNOWN_HOLD'):
        gateway.execute(request)
    assert len([r for r in journal.all() if r['kind']=='PRODUCTION_EFFECT_COMMIT'])==0
