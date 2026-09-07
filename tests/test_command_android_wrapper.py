from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANDROID = ROOT / "command-android"


def read(relative: str) -> str:
    return (ANDROID / relative).read_text(encoding="utf-8")


def test_android_identity_and_sdk_contract() -> None:
    gradle = read("app/build.gradle")
    assert "applicationId 'br.com.reisos.command'" in gradle
    assert "minSdk 26" in gradle
    assert "targetSdk 35" in gradle
    assert "versionCode 1" in gradle
    assert "versionName '0.1.0'" in gradle


def test_manifest_forbids_cleartext_and_backup() -> None:
    manifest = read("app/src/main/AndroidManifest.xml")
    assert 'android:usesCleartextTraffic="false"' in manifest
    assert 'android:allowBackup="false"' in manifest
    assert "android.permission.INTERNET" in manifest
    assert "android.permission.ACCESS_NETWORK_STATE" in manifest


def test_webview_security_locks() -> None:
    source = read("app/src/main/java/br/com/reisos/command/MainActivity.java")
    assert "setAllowFileAccess(false)" in source
    assert "setAllowContentAccess(false)" in source
    assert "MIXED_CONTENT_NEVER_ALLOW" in source
    assert "setSupportMultipleWindows(false)" in source
    assert "setAcceptThirdPartyCookies(webView, false)" in source
    assert "addJavascriptInterface" not in source
    assert '"https".equalsIgnoreCase' in source
    assert "request.hasGesture()" in source


def test_endpoint_is_configurable_and_default_is_non_routable() -> None:
    gradle = read("app/build.gradle")
    assert "COMMAND_URL" in gradle
    assert "https://command.reis-os.invalid/command-ui" in gradle
    source = read("app/src/main/java/br/com/reisos/command/MainActivity.java")
    assert 'host.endsWith(".invalid")' in source


def test_shell_contains_no_provider_or_api_secret() -> None:
    payload = "\n".join(
        path.read_text(encoding="utf-8")
        for path in ANDROID.rglob("*")
        if path.is_file()
    ).lower()
    assert "sk-proj-" not in payload
    assert "openai_api_key=" not in payload
    assert "anthropic_api_key=" not in payload
    assert "gemini_api_key=" not in payload


def test_build_workflow_packages_apk_and_checksum() -> None:
    workflow = (ROOT / ".github/workflows/command-android-apk.yml").read_text(encoding="utf-8")
    assert "assembleDebug" in workflow
    assert "sha256sum" in workflow
    assert "app-debug.apk" in workflow
    assert "upload-artifact" in workflow
