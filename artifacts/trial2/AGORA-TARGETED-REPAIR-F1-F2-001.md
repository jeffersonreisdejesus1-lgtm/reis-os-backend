# AGORA-TARGETED-REPAIR-F1-F2-001

SOURCE_ASSURANCE = SYNESIS-TRIAL2-STRICT-INDEPENDENT-ASSURANCE-001
SOURCE_REVIEW = 5165535275
PR = #84
PRE_REPAIR_HEAD = 260625884fd17c072c295b4a170ca7595b3a2f73

F1 = IDEMPOTENCY_KEY_PAYLOAD_MISMATCH_NOT_FAIL_CLOSED
REPAIR = same mission + idempotency key now compares persisted payload hash to requested payload hash; mismatch raises HOLD before any effect insert or receipt creation for the conflicting request.
EXPECTED_MUTATION_COUNT_ON_MISMATCH = 0

F2 = HANDOFF_ENVELOPE_INTEGRITY_HASH_NOT_REVALIDATED
REPAIR = persisted envelope JSON is decoded and its canonical hash is recomputed inside the same transaction before handoff acceptance; mismatch raises HOLD before actor-switch mutation. Restart recovery performs the same envelope integrity validation before reconstructing an accepted current handoff.
EXPECTED_ACTOR_SWITCH_ON_MISMATCH = 0

RUNTIME_PATH = app.single_surface_trial.trial2_asgi now instantiates IntegrityCheckedTrial2Store.
REGRESSION_TESTS = tests/test_trial2_integrity_repairs.py
LEGACY_PERSISTENCE_SUITE = tests/test_trial2_persistent_store.py now exercises IntegrityCheckedTrial2Store.

TEST_EXECUTION_AFTER_REPAIR = NOT_CLAIMED
REASON = no independent executable CI/substrate result produced in this repair step
POSTGRESQL_CONTAINER_EXECUTION = NOT_PROVEN
OPTION_A_RUNTIME_PASS = NOT_CLAIMED

PRODUCTION = NOT_AUTHORIZED
MERGE = NOT_AUTHORIZED
SELF_ASSURANCE = NOT_PERFORMED
REPLIT_FOR_OCS = FORBIDDEN

NEXT_GATE = SYNESIS_F1_F2_RECHECK_PLUS_SUBSTRATE_RESERVATION
