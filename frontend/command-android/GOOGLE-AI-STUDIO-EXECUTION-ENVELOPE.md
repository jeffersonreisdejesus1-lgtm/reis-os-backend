# GOOGLE AI STUDIO EXECUTION ENVELOPE

MISSION: COMMAND_ANDROID_PRODUCT_SLICE_E2E_001
EXECUTION_ENGINE: GOOGLE_AI_STUDIO / GEMINI
REPOSITORY: jeffersonreisdejesus1-lgtm/reis-os-backend
BRANCH: dedala/command-android-e2e-longitudinal-001
EXPECTED_HEAD: 17005f8846e5f144eff95460b05d2f4623f0eefa

## Objective

Execute and falsify the complete Command Android longitudinal product slice in one run. Do not decompose this into microgates. Return one final evidence package and one verdict.

## Hard boundaries

- synthetic product slice only
- no live backend
- no Postgres
- no real Atlas/L5 hydration
- no AI runtime integration into Command
- no Kernel mutation
- no production-readiness claim
- no real-device/TalkBack/focus/contrast claim unless a real device test is actually performed

## Required repository checks

1. Confirm the checked-out commit exactly matches EXPECTED_HEAD. If not, STOP with `HEAD_MISMATCH`.
2. Confirm `frontend/command-android/build.gradle.kts` uses `com.android.application`.
3. Confirm application id is `com.reisos.command`.
4. Confirm `AndroidManifest.xml` exposes `reisos.command.app.MainActivity` as MAIN/LAUNCHER.
5. Confirm no `android.permission.INTERNET` is declared.

## Required execution

Run from repository root:

```bash
gradle --no-daemon -p frontend/command-android clean lintDebug testDebugUnitTest assembleDebug
```

The run is PASS only if the Gradle command exits 0.

## Required test suites

All of these JUnit XML files must exist and have `failures="0"` and `errors="0"`:

- `ContractChecks`
- `LongitudinalFlowChecks`
- `ProductSliceE2EChecks`
- `ProductDataCatalogChecks`
- `ProductJourneyChecks`
- `DecisionLifecycleChecks`

## Required APK proof

Locate the debug APK under:

`frontend/command-android/build/outputs/apk/debug/`

Using Android build-tools `aapt dump badging`, prove:

- package = `com.reisos.command`
- launchable activity = `reisos.command.app.MainActivity`

## Required semantic proof

The execution must prove all of the following from tests and/or direct source/readback:

- S0 through S9 are modelled.
- all ten canonical OCS entries are present and unique.
- unknown progress cannot render as fabricated percentage.
- missing OCS generation remains PARTIAL.
- unknown graph relation produces HOLD.
- EXECUTED without matching readback is not VERIFIED.
- AUTHORIZED requires authority reference.
- VERIFIED requires readback reference.
- ASSURED requires evidence reference.
- EXECUTED cannot skip directly to ASSURED.
- Founder observation journey crosses evidence before stronger claims.
- OCS inspection journey crosses evidence before stronger claims.
- navigation can traverse and rewind.
- recreation state restores route/history.
- live backend, Postgres, real Atlas/L5, AI runtime and Kernel mutation remain closed.

## Adversarial falsification requirements

Attempt to falsify at least these claims:

1. Remove/omit generation from an OCS projection and verify the result does not become COMPLETE.
2. Present EXECUTED receipt with no readback and verify it does not become VERIFIED.
3. Present unknown graph relation and verify it does not become canonical causal truth.
4. Attempt lifecycle jump EXECUTED -> ASSURED and verify rejection.
5. Attempt assurance without evidence and verify rejection.
6. Attempt verification without readback and verify rejection.
7. Search manifest/source for INTERNET permission or network dependency.
8. Search source for live persistence, Postgres, real Atlas/L5, AI runtime, or Kernel mutation dependency.

## Evidence package to return

Return exactly one structured result containing:

```text
MISSION=COMMAND_ANDROID_PRODUCT_SLICE_E2E_001
HEAD=<exact sha>
GRADLE_BUILD=<PASS|FAIL>
LINT=<PASS|FAIL>
UNIT_TESTS=<PASS|FAIL>
LONGITUDINAL_FLOW=<PASS|FAIL>
PRODUCT_SLICE_E2E=<PASS|FAIL>
PRODUCT_CATALOG=<PASS|FAIL>
PRODUCT_JOURNEYS=<PASS|FAIL>
DECISION_LIFECYCLE=<PASS|FAIL>
APK_PRESENT=<PASS|FAIL>
APK_PACKAGE=<value>
APK_LAUNCHER=<value>
TEN_OCS_ROSTER=<PASS|FAIL>
S0_S9=<PASS|FAIL>
BOUNDARY_OFFLINE=<PASS|FAIL>
LIVE_BACKEND=false
POSTGRES=false
REAL_ATLAS_L5=false
AI_RUNTIME=false
KERNEL_MUTATION=false
REAL_DEVICE_ACCESSIBILITY=<NOT_PROVEN|PASS if materially tested>
OPEN_BLOCKING_FINDINGS=<integer>
VERDICT=<PASS|PASS_WITH_RESERVATIONS|HOLD>
```

Also attach or preserve:

- APK
- lint report
- all JUnit XMLs
- APK badging output
- exact command output/log
- any failing assertion with file/line or test name

## Verdict rules

`PASS` requires all required execution/test/APK/semantic checks passing and zero blocking findings.

`PASS_WITH_RESERVATIONS` may only be used for explicitly non-blocking reservations that do not invalidate the synthetic product-slice claims.

`HOLD` is mandatory for build failure, missing required test evidence, HEAD mismatch, broken invariant, forbidden runtime boundary, or inability to produce the required evidence package.

Do not infer production readiness, live integration, real-device accessibility, or institutional runtime truth from this execution.
