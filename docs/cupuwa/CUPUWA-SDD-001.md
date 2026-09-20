# CUPUWA Software Design Document 001

Status: DRAFT_CANONICAL_BASELINE
Base: 0e9899b30aef4e43f4f01bbfe8d2b8599d75c3bd

## Objective

CUPUWA is the REIS OS pilot product. Its implementation is driven by explicit contracts, bounded capabilities, evidence and reversible decisions.

## Architecture

Mission -> COI ingress -> capability resolution -> governed OCS composition -> implementation contract -> bounded executor -> receipt/evidence -> qualification.

Existing boundaries are reused:
- COI and multi-OCS contracts: app/cupuwa_multi_ocs
- cognitive physiology: app/cognitive_physiology
- distributed runtime and causal missions: app/distributed_runtime
- expertise and registry: app/expertise
- governance and capability policy: app/governance_refactor

## P0 scope

Local-first Android finance product: onboarding, profile, account, balance, income/expense records, categories, navigation and persistence. No login or external service is required for P0.

## Decisions and trade-offs

- Dynamic capability routing over roster-wide activation: less fan-out, stronger auditability.
- Skills describe reusable procedure; they do not grant authority.
- Existing COI/Orchestrator/runtime boundaries are extended by adapters, not replaced.
- Missing capability, authority, executor or evidence fails closed.
- CodeMagic is build/rebuild validation only, not the institutional runtime.
- External agent creation is outside this SDD until a host primitive is proven.

## Quality gates

Every implementation slice must provide: bound HEAD, changed files, tests, static checks, receipts/evidence, unresolved findings and explicit limits. No PASS, merge or promotion is automatic.
