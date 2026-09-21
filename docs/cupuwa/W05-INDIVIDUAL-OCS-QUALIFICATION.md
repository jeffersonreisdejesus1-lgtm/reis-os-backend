# W05 — Individual OCS Qualification

Status: OPEN / INVENTORY_REQUIRED / NOT_QUALIFIED

Program: REIS-OS-INSTITUTIONAL-RUNTIME-COMPLETION-001

## Objective

Reconcile the canonical OCS pool and qualify each entry by evidence. Registry
membership or selection is not equivalent to operational qualification.

## Base

- repository: jeffersonreisdejesus1-lgtm/reis-os-backend
- base head: c7903fafff7304ae7b3b69a724f35e66c2e70776
- branch: cupuwa/ocs-individual-qualification-001
- W03: PASS_WITH_LIMITS

## Required matrix

For every canonical OCS:

- OCS identifier;
- declared capabilities;
- physiology source;
- implementation source;
- host availability;
- runtime binding;
- runtime enforcement;
- execution evidence;
- tests and exact HEAD;
- receipts/artifacts;
- status: PROVEN, PARTIAL, NOT_PROVEN, or UNKNOWN.

## Rules

- pool count is not proof;
- registry entry is not proof;
- documentation is not execution proof;
- one OCS's evidence cannot generalize to another;
- missing evidence remains NOT_PROVEN or UNKNOWN;
- no authority is created by qualification;
- no OCS is promoted automatically.

## Deliverables

D01 canonical inventory;
D02 physiology/runtime matrix;
D03 evidence index;
D04 gaps and residual risks;
D05 qualification result per OCS;
D06 consolidated count with explicit denominator.

## Non-goals

- no external worker;
- no multi-host proof;
- no Orchestrator expansion;
- no CUPUWA product effect;
- no merge or promotion.

## Acceptance

W05 may close only with a reproducible matrix and explicit evidence references
for every claimed status. The expected result may be PARTIAL or NOT_PROVEN.
