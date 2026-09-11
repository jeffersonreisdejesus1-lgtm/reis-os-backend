# ÁGORA — EXTERNAL QUALIFICATION

QUALIFICATION_ID
= AGORA-QUALIFICATION-AI-MUTATION-ISOLATION-V1-001

MISSION_ID
= REIS-AI-MUTATION-ISOLATION-V1-001

TARGET_HEAD
= 3c53040ff67202e8e525b674495ff15c47ab8dce

RENDER_SERVICE
= reis-os-ai-mutation-isolation-v1
= srv-daho9vqd0e5s73883rr0

DEPLOY_ID
= dep-dahoa0id0e5s73883thg

PLAN
= FREE

STATUS
= LIVE

BUILD_QUALIFICATION
= pytest selected integrated suite
= tests/test_authority_gateway.py
= tests/test_credential_broker.py
= tests/test_production_gateway_host_bridge_integration.py
= 14 tests expected/required by selected files
= build/deploy succeeded

NEGATIVE CASES QUALIFIED
- raw credential request by AI/OCS -> DENY
- provider isolation absent -> DENY
- direct AI write still present in attestation -> DENY
- alternate write paths not reviewed -> DENY
- replay of one-shot grant -> DENY
- wrong host executor -> DENY
- mission/payload/cost/expiry/merge Authority Gateway negatives remain covered

POSITIVE CASE
- exact governed authority + valid provider isolation attestation -> opaque one-shot grant -> approved host consume -> replay denied

BOUNDARY
This qualification proves software behavior. It does NOT prove that real GitHub/Render/Vercel write credentials have already been revoked from every AI-facing connector.

INCREMENTAL_PAID_SPEND
= 0
