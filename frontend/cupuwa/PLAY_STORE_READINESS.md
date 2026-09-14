# CUPUWA — Play Store readiness checklist

Baseline: `0.3.0-mvp` / versionCode `4`

## Source-level readiness
- [x] Android application id fixed: `com.jsonsoftware.cupuwa`
- [x] compileSdk 36
- [x] targetSdk 36
- [x] minSdk 23
- [x] Java 17
- [x] no INTERNET permission in source manifest
- [x] offline local persistence
- [x] deterministic BRL math tests
- [x] daily and monthly summary logic
- [x] Play Store listing candidate
- [x] privacy-policy candidate
- [x] Data safety candidate
- [x] CodeMagic workflow emits debug APK + unsigned release AAB candidate and evidence

## Material gates still required
- [ ] CodeMagic exact-head build passes unit tests
- [ ] CodeMagic lint passes
- [ ] debug APK exists with SHA-256 evidence
- [ ] unsigned release AAB exists with SHA-256 evidence
- [ ] package/label/launcher are verified from built APK
- [ ] no INTERNET permission verified from built artifact
- [ ] install on real device or representative emulator
- [ ] cold start and persistence-after-restart proven
- [ ] add/edit/delete and BRL `25,90` scenario proven
- [ ] final screenshots captured from approved build
- [ ] production keystore/signing configured in authorized release surface
- [ ] signed AAB built from approved source revision
- [ ] public privacy-policy URL supplied
- [ ] public support email supplied
- [ ] Play Console Data safety declaration completed against signed AAB
- [ ] Play Console Financial features declaration completed
- [ ] content rating / target audience / ads declarations completed
- [ ] closed testing requirements completed if applicable to the developer account
- [ ] SÝNESIS release assurance
- [ ] Founder production-go decision

## Current policy note
For new mobile apps submitted after 31 August 2026, Google Play requires Android 16 / API 36 or higher. This baseline is configured to target API 36. Before actual submission, re-check the live Play Console policy because store requirements can change.

CUPUWA is a money-management app. The Play Console Financial features declaration must be completed for published apps; classify the exact feature set conservatively and do not represent CUPUWA as banking, lending, payments, investment custody or regulated financial advice unless those functions are actually added and qualified.

`SOURCE_READY_CANDIDATE != BUILD_PASS`
`BUILD_PASS != DEVICE_PROVEN`
`DEVICE_PROVEN != STORE_APPROVED`
