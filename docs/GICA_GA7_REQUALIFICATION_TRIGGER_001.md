# GICA GA7 Current-Head Requalification Trigger 001

TRIGGER_ID = GICA-GA7-CURRENT-HEAD-REQUALIFICATION-TRIGGER-001

PROGRAM = GICA / REIS OS

HISTORICAL_GA7_EVIDENCE_HEAD = b960ed3621bb6adc1851fdd58631d3606de8b2a3

PREVIOUS_CANONICAL_LEDGER_HEAD = 3833c9fa1c3ddb04e83363f44aeddfe7104f9a0d

PURPOSE = Trigger the dedicated GA7 current-head requalification workflow after the workflow itself was materialized.

SCOPE = Execute tests/test_gica_ga7_minimum_substrate.py plus Ruff and Mypy against the exact branch head checked out by the dedicated workflow.

NO_PROMOTION = TRUE
GA8_ENTRY = NOT_AUTHORIZED
MERGE = NOT_AUTHORIZED
AUTHORITY_EXPANSION = NOT_AUTHORIZED
TRUST_ROOT_CHANGE = NOT_AUTHORIZED

The workflow result is evidence only. It does not self-promote GA7 and does not authorize GA8.
