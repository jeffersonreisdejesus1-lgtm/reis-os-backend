# REIS-OS-COMMAND-B7-TEN-OCS-DOSSIERS-001

Status: implemented on branch
Base SHA: 591d0c4c0dcf13a2ad4b3c4463a68b4446b020c7

B7 materializes exactly ten versioned OCS dossiers using canonical profile declarations plus same-OCS runtime events from the Command event store.

Each dossier exposes identity, capability, authority, expertise, current state, evidence refs, freshness, source, version and institutional relations. Capability and authority remain distinct. Runtime absence is represented as `unknown`; it is never promoted to current or healthy. Runtime evidence is filtered by exact `ocs_id`, prohibiting cross-OCS memory/state import.

Query surfaces:
- `GET /v1/command/dossiers`
- `GET /v1/command/dossiers/{ocs_slug}`

No cross-OCS memory import is performed. No authority is inferred from capability. B8+ is not implemented in this branch.
