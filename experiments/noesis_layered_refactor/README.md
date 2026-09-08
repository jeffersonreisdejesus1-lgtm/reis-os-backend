# Nóesis layered physiology refactor — deterministic reproduction

This directory is a **noncanonical candidate overlay** for the current Nóesis `EC-NOESIS-007`. It does not replace or rewrite the canonical runtime.

## Exact baseline

Canonical package:

`NOESIS_NATIVE_EC007_20260823_v0.2.1.zip`

SHA-256:

`691d738823b52265af6a268a287e3475e446a4b7f3aaec681856b3f27cdcd06c`

Canonical IDI:

`REISOS::INST::NOESIS::001`

Canonical EC:

`EC-NOESIS-007`

Expected native L0 binding hash:

`650ce1748e368055d79cf97db887f71976141f434afa589ae924e07fb7dc605f`

## What is additive

`layered.py` adds mechanism around the unchanged native cognitive engine:

1. R1 explicit blackboard/state;
2. R2 progress monitor;
3. R3 typed transitions;
4. R4 scheduler;
5. R5 telemetry;
6. R6 formal runtime checks.

The native `Noesis.process()` remains the cognitive step. The candidate does not grant itself institutional authority.

## Reproduction

1. Recover the exact canonical ZIP above and verify its SHA-256.
2. Extract it to a clean temporary directory.
3. Put that extraction on `PYTHONPATH` so `noesis.runtime` resolves to the exact canonical runtime.
4. Put this repository root on `PYTHONPATH` as well.
5. Run:

```bash
python -m pytest -q experiments/noesis_layered_refactor/test_layered.py
```

For a full candidate-package replay, apply the candidate overlay to a fresh extraction and run the complete canonical + candidate test suite. The sealed builder replay produced `112/112 PASS`; the original baseline produced `100/100 PASS`.

## Causal stage comparison

The six layers can be activated cumulatively with `max_stage`:

- R1 is the control with explicit state only;
- R2 makes stagnation observable and terminal when no scheduler is present;
- R3 adds typed, non-authority-transferring relations;
- R4 turns stagnation into a method change when the phase allows it;
- R5 adds a hash-chained operational trail;
- R6 checks L0 binding/identity/EC, stop consistency, scheduler authority and telemetry integrity.

This staged activation is intentional: it preserves causal attribution instead of switching every mechanism on at once.

## Sealed receipts

- Candidate package SHA-256: `55fab30eb97289b8f1c977b9d63c8c07d08d97a4d015dcfde8fc9dc3ac706f14`
- Qualification report SHA-256: `c2e4a5f891fbdcbd1e4d141b3dc80638f285564a77a13944c5b62a041bfc5b87`
- Candidate manifest SHA-256: `69f359ef3857f241ce8f0ea7214c0bf6e5eb1ccab02bfa14c60c34ab9c4af067`
- Patch SHA-256: `5a73d8b59783d654683f88a5931ca0a6bc6618ed6ad5946ff0d785a56c6c7f95`

## Boundaries

`L1..L6 MAY CONTROL MECHANISM`

`L1..L6 MUST NOT ALTER IDENTITY`

`ORCHESTRATION != AUTHORITY`

`HANDOFF != AUTHORITY_TRANSFER`

`BUILDER_ROLE != FINAL_ASSURANCE_ROLE`

No production, canonical promotion, merge, adoption or self-assurance is authorized by this candidate.