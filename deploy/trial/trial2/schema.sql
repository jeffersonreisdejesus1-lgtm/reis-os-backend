BEGIN;

CREATE TABLE IF NOT EXISTS trial2_missions (
  mission_id VARCHAR(128) PRIMARY KEY,
  canonical_state_ref VARCHAR(256) NOT NULL,
  current_gate VARCHAR(128) NOT NULL,
  status VARCHAR(64) NOT NULL,
  active_ocs_id VARCHAR(64),
  active_instance_id VARCHAR(128),
  current_handoff_ref VARCHAR(128),
  autonomy_budget INTEGER NOT NULL,
  autonomous_step_counter INTEGER NOT NULL DEFAULT 0,
  autonomous_handoff_counter INTEGER NOT NULL DEFAULT 0,
  repair_cycle_counter INTEGER NOT NULL DEFAULT 0,
  version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS trial2_bindings (
  binding_id VARCHAR(128) PRIMARY KEY,
  mission_id VARCHAR(128) NOT NULL,
  ocs_id VARCHAR(64) NOT NULL,
  instance_id VARCHAR(128) NOT NULL,
  generation INTEGER NOT NULL,
  fencing_epoch INTEGER NOT NULL,
  authority_ref VARCHAR(256) NOT NULL,
  role VARCHAR(128) NOT NULL,
  status VARCHAR(64) NOT NULL,
  checkpoint_ref VARCHAR(128),
  created_at VARCHAR(64) NOT NULL,
  CONSTRAINT uq_trial2_binding_instance UNIQUE (mission_id, instance_id)
);

CREATE TABLE IF NOT EXISTS trial2_fencing (
  mission_id VARCHAR(128) NOT NULL,
  ocs_id VARCHAR(64) NOT NULL,
  epoch INTEGER NOT NULL,
  PRIMARY KEY (mission_id, ocs_id)
);

CREATE TABLE IF NOT EXISTS trial2_checkpoints (
  checkpoint_id VARCHAR(128) PRIMARY KEY,
  mission_id VARCHAR(128) NOT NULL,
  instance_id VARCHAR(128) NOT NULL,
  ocs_id VARCHAR(64) NOT NULL,
  sequence INTEGER NOT NULL,
  canonical_state_ref VARCHAR(256) NOT NULL,
  local_state_json TEXT NOT NULL,
  local_state_hash VARCHAR(64) NOT NULL,
  created_at VARCHAR(64) NOT NULL,
  CONSTRAINT uq_trial2_checkpoint_sequence UNIQUE (mission_id, sequence)
);

CREATE TABLE IF NOT EXISTS trial2_handoffs (
  handoff_id VARCHAR(128) PRIMARY KEY,
  mission_id VARCHAR(128) NOT NULL,
  route_id VARCHAR(180) NOT NULL,
  source_ocs_id VARCHAR(64) NOT NULL,
  source_instance_id VARCHAR(128) NOT NULL,
  target_ocs_id VARCHAR(64) NOT NULL,
  target_instance_id VARCHAR(128) NOT NULL,
  checkpoint_ref VARCHAR(128) NOT NULL,
  envelope_json TEXT NOT NULL,
  envelope_hash VARCHAR(64) NOT NULL,
  accepted BOOLEAN NOT NULL DEFAULT FALSE,
  acceptance_receipt_ref VARCHAR(128),
  created_at VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS trial2_receipts (
  receipt_id VARCHAR(128) PRIMARY KEY,
  mission_id VARCHAR(128) NOT NULL,
  kind VARCHAR(64) NOT NULL,
  payload_json TEXT NOT NULL,
  payload_hash VARCHAR(64) NOT NULL,
  created_at VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS trial2_observability_events (
  event_id VARCHAR(128) PRIMARY KEY,
  mission_id VARCHAR(128) NOT NULL,
  from_identity VARCHAR(64),
  from_instance VARCHAR(128),
  to_identity VARCHAR(64),
  to_instance VARCHAR(128),
  role VARCHAR(128),
  gate VARCHAR(128) NOT NULL,
  authority_ref VARCHAR(256),
  fencing_epoch INTEGER,
  state_before_hash VARCHAR(64) NOT NULL,
  state_after_hash VARCHAR(64) NOT NULL,
  handoff_ref VARCHAR(128),
  receipt_ref VARCHAR(128),
  checkpoint_ref VARCHAR(128),
  outcome VARCHAR(64) NOT NULL,
  created_at VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS trial2_effects (
  effect_id VARCHAR(128) PRIMARY KEY,
  mission_id VARCHAR(128) NOT NULL,
  instance_id VARCHAR(128) NOT NULL,
  ocs_id VARCHAR(64) NOT NULL,
  fencing_epoch INTEGER NOT NULL,
  authority_ref VARCHAR(256) NOT NULL,
  idempotency_key VARCHAR(128) NOT NULL,
  payload_hash VARCHAR(64) NOT NULL,
  receipt_ref VARCHAR(128) NOT NULL,
  created_at VARCHAR(64) NOT NULL,
  CONSTRAINT uq_trial2_effect_idempotency UNIQUE (mission_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS trial2_state_entries (
  mission_id VARCHAR(128) NOT NULL,
  namespace_key VARCHAR(320) NOT NULL,
  value_hash VARCHAR(64) NOT NULL,
  last_instance_id VARCHAR(128) NOT NULL,
  last_epoch INTEGER NOT NULL,
  PRIMARY KEY (mission_id, namespace_key)
);

COMMIT;
