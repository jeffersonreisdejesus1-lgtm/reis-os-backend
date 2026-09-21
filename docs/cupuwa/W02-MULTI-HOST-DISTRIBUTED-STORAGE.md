# W02 — Multi-Host Distributed Storage

Status: OPEN / ARCHITECTURE_DEFINED / IMPLEMENTATION_NOT_STARTED

Program: REIS-OS-INSTITUTIONAL-RUNTIME-COMPLETION-001

## Objective

Prove operation ownership, durable storage, recovery and reconciliation
between independent machines, extending the bounded local POSIX result without
reopening it.

## Base

- repository: jeffersonreisdejesus1-lgtm/reis-os-backend
- base head: 6560a38160fe0369e31fa0d7402e48bac5100984
- branch: cupuwa/multi-host-distributed-storage-001
- W01: PASS_WITH_LIMITS

## Required architecture

Client/process A
-> authenticated network transport
-> approved remote durable store
-> client/process B

The backend must provide:

- operation_id uniqueness;
- payload fingerprint conflict detection;
- atomic ownership/lease;
- fencing or stale-owner rejection;
- durable receipt persistence;
- readback after write;
- recovery after process or host failure;
- explicit UNKNOWN/HOLD;
- no blind retry;
- authority reference preservation.

## Required probes

M01 — remote write/read across hosts
M02 — cross-host concurrent claim
M03 — network timeout and uncertain write
M04 — stale lease/fencing
M05 — host loss and recovery
M06 — replay after recovery
M07 — conflicting payload
M08 — receipt corruption/mismatch
M09 — authority_ref preservation
M10 — deterministic evidence and hashes

## Infrastructure boundary

No provider, database, disk, credential or paid service is created by this
record. A backend may be selected only after authorization and a reproducible
test environment is available.

## Acceptance

W02 can only be qualified after M01–M10 execute across independent hosts with
logs, receipts, versions, hashes and an explicit failure model.

## Non-goals

- no Orchestrator integration;
- no worker/agent dispatch;
- no 72-OCS qualification;
- no CUPUWA product effect;
- no merge or promotion.
