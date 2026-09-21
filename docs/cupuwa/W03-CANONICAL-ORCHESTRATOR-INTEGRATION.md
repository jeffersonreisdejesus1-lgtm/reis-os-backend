# W03 — Canonical Orchestrator Integration

Status: OPEN / CONTRACT_DEFINED / IMPLEMENTATION_NOT_STARTED

Program: REIS-OS-INSTITUTIONAL-RUNTIME-COMPLETION-001

## Objective

Connect a real mission flow to the existing canonical Orchestrator boundary,
without creating a parallel orchestrator or expanding authority.

## Base

- repository: jeffersonreisdejesus1-lgtm/reis-os-backend
- base head: 0a6e750f71c24d8c88598e3aeeb251086c3716f5
- branch: cupuwa/orchestrator-integration-001
- local Skills and local distributed storage remain bounded foundations

## Required path

Mission
-> authority validation
-> capability resolution
-> OCS composition
-> Orchestrator dispatch decision
-> local executor boundary
-> receipt
-> durable readback
-> mission result

## Required controls

- mission identity preserved;
- operation_id remains canonical;
- authority is validated before dispatch;
- capability does not create authority;
- OCS assignment is explicit;
- missing or ambiguous composition fails closed;
- executor absence fails closed;
- replay does not create a second effect;
- receipts do not imply promotion;
- no parallel Orchestrator is created.

## Required probes

O01 valid mission reaches the canonical Orchestrator boundary;
O02 missing authority is rejected;
O03 capability outside mission is rejected;
O04 incomplete OCS composition is rejected;
O05 missing executor fails closed;
O06 replay returns the canonical operation;
O07 result and receipt remain linked;
O08 restart/readback preserves causal identity.

## Non-goals

- no multi-host proof;
- no external worker or agent dispatch;
- no individual qualification of 72 OCSs;
- no CUPUWA material effect;
- no merge or promotion.

## Acceptance

W03 is qualified only after the actual canonical Orchestrator is identified,
the probes execute against it, and evidence is independently reproducible.
