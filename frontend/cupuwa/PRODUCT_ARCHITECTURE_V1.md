# CUPUWA — Product Real Architecture v1

Status: IMPLEMENTATION CONTRACT / bounded to local-first Android product lane.

## Product thesis
CUPUWA is a personal financial operating surface, not a two-button ledger. The first publishable product must let a user understand money, organize it and act on it without pretending that external bank connectivity exists.

## Navigation
Bottom navigation: Início / Movimentos / Planejar / Insights / Ajustes.

## End-to-end local capabilities
1. Onboarding: local profile/name, monthly income reference, initial account/wallet and optional opening balance.
2. Dashboard: consolidated balance, month income/expense/result, budget progress, goals progress, recent movements and contextual insight.
3. Movements: create/edit/delete/search/filter income and expense; category, account, description and date are persisted.
4. Accounts/wallets: create/edit/archive cash, checking, savings, wallet and other local accounts; opening/current balance.
5. Categories: system defaults plus custom categories; income/expense type.
6. Budgets: monthly spending limit by category; deterministic spent/remaining/progress calculation.
7. Goals: target amount, saved amount, optional target date, progress and contributions.
8. Reports: current-month category totals, income vs expense, savings/result and simple period summaries.
9. Insights: deterministic local rules only (overspending, budget pressure, positive/negative month, largest expense category, goal progress). No claim of cloud AI.
10. Settings: profile, currency BRL, privacy/local-data statement, reset local data with confirmation.

## State model
Every functional surface must define useful empty state and success state. Mutations require validation. Destructive actions require confirmation. No button may represent an unavailable integration as operational.

## Persistence
Local-first persistence. Existing ledger data must remain readable. New structured records are versioned in app-local storage. No INTERNET permission is introduced in this increment.

## External capability boundary
Not implemented/claimed in the local product lane: Open Finance, bank OAuth, WhatsApp OTP, Google/Apple account login, cloud synchronization, card issuing, investments, lending, payment initiation or remote AI. These require separate services, credentials, privacy/security review and explicit authority.

## Experience direction
Original CUPUWA identity: light warm-neutral surface, deep plum/ink hierarchy, violet accent, strong information hierarchy, large financial numbers, cards with purposeful density, consistent bottom navigation. Pierre screenshots are depth/flow benchmark only; no visual, copy or brand cloning.

## Acceptance
A feature counts only when its data model, persistence, user mutation path and rendered state are wired end-to-end. BUILD_PASS remains evidence-bound to material CI/build execution.