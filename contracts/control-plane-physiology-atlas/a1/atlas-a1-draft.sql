-- A1 DDL ARTIFACT ONLY — DO NOT APPLY IN A1.
-- POSTGRES_APPLY = NOT_AUTHORIZED
-- This file records the future persistence shape without creating a migration.

CREATE TABLE atlas_catalog_release_draft (
    catalog_scope_id text NOT NULL,
    release_id text NOT NULL,
    semantic_catalog_sha text NOT NULL,
    predecessor_release_id text,
    status text NOT NULL,
    PRIMARY KEY (catalog_scope_id, release_id)
);

CREATE TABLE atlas_served_catalog_pointer_draft (
    catalog_scope_id text PRIMARY KEY,
    served_catalog_release_id text NOT NULL
);

-- No migration imports this artifact. No runtime code executes it.
