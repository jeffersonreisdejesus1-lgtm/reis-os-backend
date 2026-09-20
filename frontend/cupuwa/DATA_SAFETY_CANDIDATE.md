# CUPUWA — Data safety candidate (MVP 0.3.0)

This record is a preparation aid for Google Play Console. Final answers must be verified against the exact signed release build submitted to Google Play.

## Current source baseline
- No `android.permission.INTERNET` declaration.
- No account/authentication.
- No backend or cloud synchronization.
- No advertising SDK.
- No analytics SDK.
- No bank integration.
- User-entered financial movements are stored locally in app-private SharedPreferences.

## Candidate interpretation
Based on the current source only, financial movement data is processed locally on-device and is not transmitted by CUPUWA to J-SON Software or third parties.

## Do not finalize automatically
Before Play Console submission, TÊMIS/Founder must compare this record with:
1. exact signed AAB;
2. merged manifest/dependencies;
3. any store-added SDK/configuration;
4. final privacy policy;
5. current Google Play Data safety questionnaire wording.

If future versions add cloud AI, analytics, bank connections, remote backup or accounts, this candidate is invalid and must be regenerated.

`SOURCE_BASED_CANDIDATE = TRUE`
`FINAL_PLAY_CONSOLE_DECLARATION = NOT_YET_SUBMITTED`
