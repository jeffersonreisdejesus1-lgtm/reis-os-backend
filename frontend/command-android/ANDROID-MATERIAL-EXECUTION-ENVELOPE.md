# ANDROID MATERIAL EXECUTION ENVELOPE

MISSION: COMMAND_ANDROID_PRODUCT_SLICE_E2E_001
EXECUTION_REQUIREMENT: REAL_SHELL + JDK_17 + ANDROID_SDK + GRADLE + AAPT + REPOSITORY_ACCESS
REPOSITORY: jeffersonreisdejesus1-lgtm/reis-os-backend
BRANCH: dedala/command-android-e2e-longitudinal-001
HEAD_RESOLUTION: resolve current PR #75 head at execution time
EXECUTION_MODE: LONGITUDINAL
MICROGATE_CADENCE: DISABLED_AS_DEFAULT

## Executor correction

Google AI Studio / Gemini Playground was materially tested as an execution surface and returned `BLOCKED (EXECUTION_ENVIRONMENT_UNAVAILABLE)`: the textual model environment has no authenticated repository checkout, shell, Android SDK, Gradle runtime, AAPT tooling, or binary artifact generation capability.

Therefore:

`GOOGLE_AI_STUDIO_TEXTUAL_MODEL != MATERIAL_ANDROID_EXECUTOR`

The canonical executor is capability-defined rather than vendor-defined. Any environment may execute this envelope only if it materially provides the required shell/toolchain/repository capabilities and can preserve the resulting evidence.

Examples include an authorized local Android build host, a provisioned cloud development environment, or a CI runner with the required toolchain and repository access. No environment is authoritative merely by product name.

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

1. Resolve the current head SHA of PR #75 and record it as `HEAD`.
2. Confirm the checked-out branch is `dedala/command-android-e2e-longitudinal-001` at that exact HEAD. If not, STOP with `HEAD_MISMATCH`.
3. Confirm `frontend/command-android/build.gradle.kts` uses `com.android.application`.
4. Confirm application id is `com.reisos.command`.
5. Confirm `AndroidManifest.xml` exposes `reisos.command.app.MainActivity` as MAIN/LAUNCHER.
6. Confirm no `android.permission.INTERNET` is declared.

## Required execution

Run from repository root:

```bash
gradle --no-daemon -p frontend/command-android clean lintDebug testDebugUnitTest assembleDebug
```

The run is PASS only if the command exits 0.

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

Also compute SHA-256 for the produced APK.

## Required semantic proof

Prove from tests and/or exact-head readback:

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

Attempt at minimum:

1. Missing generation must not become COMPLETE.
2. EXECUTED receipt without readback must not become VERIFIED.
3. Unknown graph relation must not become canonical causal truth.
4. EXECUTED -> ASSURED must be rejected.
5. Assurance without evidence must be rejected.
6. Verification without readback must be rejected.
7. Manifest/source must remain free of INTERNET permission/network dependency.
8. Source must remain free of live persistence, Postgres, real Atlas/L5, AI runtime, or Kernel mutation dependency.

## Evidence package

Return exactly one structured result:

```text
MISSION=COMMAND_ANDROID_PRODUCT_SLICE_E2E_001
HEAD=<exact sha>
EXECUTION_ENVIRONMENT=<material runtime description>
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
APK_SHA256=<value>
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

Preserve:

- APK
- lint report
- all JUnit XMLs
- APK badging output
- exact command output/log
- SHA-256 output
- any failing assertion with file/line or test name

## Verdict rules

`PASS` requires all required execution/test/APK/semantic checks passing and zero blocking findings.

`PASS_WITH_RESERVATIONS` may only be used for explicitly non-blocking reservations that do not invalidate the synthetic product-slice claims.

`HOLD` is mandatory for build failure, missing required test evidence, HEAD mismatch, broken invariant, forbidden runtime boundary, or inability to produce the required evidence package.

Do not infer production readiness, live integration, real-device accessibility, or institutional runtime truth from this execution.
