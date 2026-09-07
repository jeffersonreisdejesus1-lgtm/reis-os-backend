# REIS OS Command Android

Isolated Android shell for the current REIS OS Command web surface.

## Boundary

- baseline: PR #60 exact head `c74bdda667faf9a6913c6d212a1b0a1022513f4d`
- strategy: secure WebView shell; no native rewrite
- Command remains a projection / bounded control surface, never the institutional source of truth
- no API key, provider key, secret, canonical write authority, or embedded LLM is added by this shell
- OURO remains independent of external AI; PRATA failure does not imply OURO failure

## Build

Requires JDK 17, Android SDK 35 and Gradle 8.9.

```bash
gradle -p command-android :app:assembleDebug \
  -PCOMMAND_URL=https://YOUR_COMMAND_HOST/command-ui
```

`COMMAND_URL` must be HTTPS. If omitted, the APK intentionally uses the non-routable `.invalid` placeholder and shows a clear configuration state rather than contacting an invented endpoint.

Debug APK:

`command-android/app/build/outputs/apk/debug/app-debug.apk`

## Security posture

The wrapper disables cleartext traffic, file/content access, mixed content, multiple windows and third-party cookies. Same-origin HTTPS navigation stays inside the WebView. Gesture-initiated external HTTPS links require explicit confirmation and are delegated to the system browser. Non-HTTPS external navigation is blocked.

The wrapper exposes no `JavascriptInterface`; the existing Command UI keeps its current bearer-auth and organization-selection contracts through same-origin relative requests.

## Device proof boundary

Build success is not device proof. Installation, cold start, login, organization selection, Command navigation, OURO/PRATA, Local Lite, logout/session, offline behavior and Android back behavior must be exercised on a real Android device before claiming device PASS. TalkBack/assistive-technology remains NOT_PROVEN until materially tested.
