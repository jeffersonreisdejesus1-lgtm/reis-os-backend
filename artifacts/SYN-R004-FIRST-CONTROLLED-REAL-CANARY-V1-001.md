# SYN-R004 FIRST CONTROLLED REAL CANARY V1

CANARY_ID
= SYN-R004-FIRST-CONTROLLED-REAL-CANARY-V1-001

DOMAIN
= SOFTWARE_DELIVERY

PROVIDER
= GITHUB

TARGET
= jeffersonreisdejesus1-lgtm/reis-os-backend

BASE
= main

BRANCH
= noesis/syn-r004-production-canary-v1-001

AUTHORIZED_EFFECTS
= GITHUB_CREATE_BRANCH
= GITHUB_CREATE_OR_UPDATE_FILE
= GITHUB_OPEN_PR

GITHUB_MERGE_PR
= FORBIDDEN

COST_POLICY
= ZERO_UNAUTHORIZED_SPEND

ESTIMATED_INCREMENTAL_COST_USD
= 0.0

PAID_UPGRADE
= FALSE

PURPOSE
= Materially prove a low-risk, reversible real external effect after SYN-R004 was merged to main.

EXPECTED_RECONCILIATION
= branch exists
= canary artifact commit exists
= draft PR exists
= no merge
= no Render spend-triggering action
