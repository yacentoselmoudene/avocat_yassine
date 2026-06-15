# مكتب المحاماة — Mobile (APK)

Capacitor 6 wrapper around the Django web app. Pure-webview on first launch
(asks for the server URL), then loads the PWA from that URL — the PWA's
service worker handles the offline-read cache.

## Prerequisites
- Node 22.x, npm 10.x
- JDK 17 (Eclipse Temurin tested)
- Android SDK with platforms 34/35 and build-tools 34+
  (`~/Library/Android/sdk` on macOS)

## Build
```
npm install
npx cap sync android
JAVA_HOME=$(/usr/libexec/java_home -v 17) \
  npm run build:debug
```

The APK lands at:
`android/app/build/outputs/apk/debug/app-debug.apk`

## What's inside

| Path | Purpose |
|---|---|
| `www/index.html` | First-launch URL chooser. Saved to localStorage and reused. |
| `capacitor.config.json` | Cleartext HTTP allowed (`androidScheme=https`, `cleartext=true`) so LAN-only deployments (`http://192.168.x.x:8003`) work without a TLS cert. |
| `android/app/src/main/res/mipmap-*/ic_launcher*.png` | Brand icon (deep green tile, Arabic glyph م). |
| `android/app/src/main/res/values/colors.xml` | Brand colors for status bar + theme. |
| `android/app/src/main/res/values/ic_launcher_background.xml` | Adaptive-icon background. |

## Sideload to a device
```
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
```
Or copy `app-debug.apk` to the device and tap it (requires "install unknown
apps" permission for the file manager).

## Release build (signed)

The build.gradle reads `android/app/signing.properties` automatically — if
present, the release task signs the APK; if absent, the release APK stays
unsigned (debug builds always signed by the Android debug keystore).

A dev keystore + signing.properties are already committed locally (NOT in
git — see `.gitignore`). Default credentials:

```
storeFile=release.jks      alias=avocat
storePassword=avocat_dev_2026
keyPassword=avocat_dev_2026
```

To rotate (mandatory before any production deploy):
```
cd android/app
keytool -genkey -v -keystore release.jks -alias avocat \
  -keyalg RSA -keysize 4096 -validity 10000
# update signing.properties with the passwords you chose
```
Then:
```
JAVA_HOME=$(/usr/libexec/java_home -v 17) npm run build:release
```
Output: `android/app/build/outputs/apk/release/app-release.apk` (~2.9 MB).

Verify the signature:
```
~/Library/Android/sdk/build-tools/36.0.0/apksigner verify --print-certs \
  android/app/build/outputs/apk/release/app-release.apk
```

> WARNING — keep `release.jks` backed up. Losing it means you can never push
> updates to the same install on a user's device; they'd have to uninstall
> and lose local data.

## Note on Capacitor version
Pinned to 6.x because 7+ requires JDK 21. Upgrade to 7+ when the local JDK
moves to 21 — Capacitor 6 will receive security patches until late 2026.
