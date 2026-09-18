# REIS OS GitHub Repository Governance

ARCHITECTURE_ID = REIS-OS-GITHUB-GOVERNANCE-AND-MIGRATION-001

## Repository classes

- CORE: institutional backend/runtime foundations.
- PRODUCT: one important software/product per repository.
- INFRASTRUCTURE: deploy, gateway, persistence, observability or build support that is independently useful.
- DOCUMENTATION: documentation/mirror repositories only.
- ARCHIVE: historical or experimental repositories no longer active.

## Canonical rules

1. One important software = one identifiable repository.
2. `reis-os-backend` is not a dumping ground for unrelated products.
3. GitHub is the canonical source-control home after migration from Replit.
4. Automatic GitHub Actions are exception-based. Default CI policy while cost is constrained is `MANUAL_ONLY` unless a workflow has a current operational need.
5. Experimental or obsolete workflows are removed from active execution; history remains in Git.
6. Repository deletion requires an explicit destructive decision. Archive is preferred before delete.
7. `MERGE != PRODUCTION` and code integration does not authorize runtime activation.
8. `requested != executed != verified != assured != promoted`.

## Current repository map

KEEP / CORE
- reis-os-backend
- hazel-core

KEEP / PRODUCT
- kupuwa-mobile

KEEP / INFRASTRUCTURE
- hazel-core-gateway

ARCHIVE_CANDIDATE
- ex013-vector-tool
- hazel-core-audit
- reis-os-cip-r2

DOCUMENTATION
- reis-os-obsidian-vault

## Migration destination rule

A Replit software must not be imported into `reis-os-backend` merely because it belongs to REIS OS. It receives its own repository when it is an independently identifiable software. Shared institutional components may remain in an existing core repository only when their ownership and dependency boundaries are explicit.
