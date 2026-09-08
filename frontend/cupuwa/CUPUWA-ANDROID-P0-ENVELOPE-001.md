# CUPUWA Android P0 Envelope

ENVELOPE_ID = CUPUWA-ANDROID-P0-ENVELOPE-001
PATH = B
PUBLIC_APP_NAME = CUPUWA
PUBLISHER = J-SON Software
APPLICATION_ID = com.jsonsoftware.cupuwa
COMMAND_APK = KEEP_SEPARATE
IMPLEMENTATION_OWNER = SOFIA
UX_OWNER = IRIS
CONTRAST_OWNER = DEDALA@GROK

## Authorized scope

P0 is a local, offline money slice:

- display current balance;
- record income;
- record expense;
- show local history;
- persist data across app restart;
- provide deterministic unit checks for money parsing and balance calculation.

## Explicit exclusions

- no INTERNET permission;
- no backend or network client;
- no WhatsApp;
- no orders;
- no AI runtime;
- no inventory or margin;
- no Kernel mutation;
- no Command S0-S9 import;
- no com.reisos.command dependency;
- no SyntheticCommand fixture;
- no production or market-readiness claim before device assurance.

## Required identity

The CUPUWA application must use:

- namespace: com.jsonsoftware.cupuwa;
- applicationId: com.jsonsoftware.cupuwa;
- label: CUPUWA.

## Closure evidence

A material closure requires:

1. Gradle build succeeds;
2. unit tests pass;
3. APK is generated for this exact branch HEAD;
4. AAPT confirms package and launcher;
5. manifest confirms INTERNET permission is absent;
6. device test confirms income/expense, balance, history, and persistence after reboot.

Command and CUPUWA remain separate products and separate assurance objects.
