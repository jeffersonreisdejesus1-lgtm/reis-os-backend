# OCS-X Pretrial Independent Local Replay

OBJECT = OCSX-PRETRIAL-INDEPENDENT-LOCAL-REPLAY-001
SOURCE_HEAD = 2706bc5196ae1edce2354773629ce6ba978802b2
SOURCE_PR = #74
MODE = ALTERNATIVE_VERIFICATION_OUTSIDE_GITHUB_ACTIONS
TRIAL_EXECUTED = FALSE
OCS_X_CREATED = FALSE

## Source material replayed

Exact-head source reconstructed from:
- `app/ocsx_pretrial/harness.py`
- `app/ocsx_pretrial/evidence.py`
- `tests/test_ocsx_pretrial_enforcement.py`
- `tests/test_ocsx_pretrial_evidence.py`

Execution environment:
- Python `3.13.5`
- Linux `6.18.35-x86_64`

## Result

FOCUSED_CHECKS = 28
PASS = 28
FAIL = 0

Verified classes include:
- own-namespace-only synthetic mutation;
- cross-namespace denial;
- canonical / OURO / production denial;
- deny => mutation count unchanged;
- non-allowlisted tool denial;
- cognitive-input sanitation;
- proposal cannot self-authorize execution;
- external gate cannot cross authority boundary;
- single-writer enforcement;
- single-stop enforcement;
- post-stop fencing;
- NoProgress / Fail terminal fencing;
- deterministic recovery;
- L0 identity mismatch rejection;
- authority expansion during recovery rejection;
- evidence-chain tamper detection;
- missing evidence => UNKNOWN;
- STOPPED / VOID / ABORTED retention;
- reproducible checkpoint hashing;
- generation receipt deterministic hashing;
- causal deny readback zero-mutation rule;
- M01-M13 exact contract coverage;
- explicit metric threshold failure;
- identity mismatch => VOID;
- recovery readback hashing.

LOCAL_REPLAY = PASS
CODE_TEST_FAILURE = NOT_OBSERVED

## Epistemic boundary

This replay is alternative execution evidence only. It does not convert the GitHub Actions pre-step failure into PASS, does not replace independent institutional assurance, and does not authorize OCS-X creation or trial execution.

GITHUB_ACTIONS_RESERVATION = OPEN
INDEPENDENT_ASSURANCE = STILL_REQUIRED_AT_FINAL_GATE
TRIAL_AUTHORITY = NOT_GRANTED
OCS_X_CREATION = FORBIDDEN
L1_ACTIVATION = FORBIDDEN
TRIAL_EXECUTION = FORBIDDEN
PRODUCTION_ROUTING = FORBIDDEN
CANONICAL_STATE_WRITE = FORBIDDEN
ADOPTION = FORBIDDEN
MERGE = NOT_AUTHORIZED
