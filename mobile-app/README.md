# Ashley Mobile — Capacitor APK

Wrapper Capacitor que bundlea la PWA de `assets/mobile/` y la empaqueta
como APK Android instalable directamente (sin Play Store).

> Para usuarios finales: descarga el APK del Release en GitHub. Para
> desarrolladores que quieran builear localmente: continúa abajo.

## Requisitos

- **Node.js 18+** y **npm**
- **JDK 17** (Eclipse Temurin / OpenJDK)
- **Android SDK** + plataforma 33+ (vía Android Studio o `sdkmanager`)
- Variable de entorno `ANDROID_HOME` apuntando al SDK

En Windows con Android Studio típico:
```
ANDROID_HOME=C:\Users\<TU_USER>\AppData\Local\Android\Sdk
```

## Setup inicial (una sola vez)

```bash
cd mobile-app
npm run init
```

Eso ejecuta:
1. `npm install` — instala Capacitor + dependencias
2. `npm run sync-assets` — copia `assets/mobile/` del repo principal a `www/`
3. `npx cap add android` — crea el proyecto Android (`android/`)
4. `npx cap sync android` — copia assets + plugins al proyecto nativo

## Build local (debug APK)

```bash
npm run build:debug
```

El APK queda en:
```
android/app/build/outputs/apk/debug/app-debug.apk
```

Pásalo a tu móvil (USB, Telegram, Drive) y tap para instalar.

> En Android necesitarás activar **"Permitir orígenes desconocidos"** o
> **"Instalar apps desconocidas"** para Chrome / tu app de archivos.

## Build CI (GitHub Actions)

Triggered por:
- Manual: Actions → "Build Ashley Mobile APK" → Run workflow
- Tag push: `git tag mobile-v0.18.2 && git push origin mobile-v0.18.2`

Output:
- Artifact `ashley-mobile-debug-apk` (descargable desde la run de Actions)
- Release de GitHub con el APK adjunto (solo en push de tag)

Ver `.github/workflows/build-android-apk.yml`.

## Build release (firmado con keystore propio)

Para distribución sin warnings de Play Protect, necesitas keystore propio
(no debug). Generar uno:

```bash
keytool -genkey -v -keystore ashley-release.keystore \
  -alias ashley -keyalg RSA -keysize 2048 -validity 10000
```

Configurar en `android/app/build.gradle`:
```gradle
android {
    signingConfigs {
        release {
            storeFile file('ashley-release.keystore')
            storePassword 'tu_password'
            keyAlias 'ashley'
            keyPassword 'tu_password'
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
        }
    }
}
```

```bash
npm run build:release
# o para .aab (Play Store)
npm run build:bundle
```

> ⚠️ NUNCA commits del keystore o passwords. Añádelo a `.gitignore`
> (ya está) y guárdalo en un password manager.

Para CI con keystore: GitHub Secrets `KEYSTORE_BASE64`,
`KEYSTORE_PASSWORD`, `KEY_ALIAS`, `KEY_PASSWORD`. Decodificar el base64
en el workflow antes de buildear.

## Cómo funciona el bundling

```
assets/mobile/         (source of truth, también sirve PWA en desktop)
  ├─ index.html
  ├─ app.js
  ├─ app.css
  ├─ manifest.json
  └─ sw.js
        │
        │  npm run sync-assets
        ▼
mobile-app/www/        (Capacitor web root)
  ├─ index.html        (paths fijados: /mobile/X → ./X)
  ├─ app.js
  ├─ app.css
  ├─ manifest.json     (start_url/scope → '/')
  ├─ sw.js             (cached paths fijados)
  └─ ashley_pfp.jpg    (avatar copiado de assets/)
        │
        │  npx cap sync android
        ▼
mobile-app/android/    (proyecto Android nativo)
        │
        │  gradlew assembleDebug
        ▼
app-debug.apk
```

El APK contiene la PWA bundleada — funciona offline. Las llamadas
`/api/*` de la PWA van a la URL configurada por el user (su PC en LAN
o Tailscale), interceptadas por el HTTP client de la PWA, no por
Capacitor.

## Estructura de directorios

```
mobile-app/
├── android/                  (gitignored — generado por cap add android)
├── node_modules/             (gitignored)
├── www/                      (gitignored — generado por sync-assets)
├── scripts/
│   └── sync-assets.js
├── capacitor.config.ts
├── package.json
├── package-lock.json
└── README.md (este archivo)
```

## Troubleshooting

### `cap add android` falla con "ANDROID_HOME not set"

Configura la variable de entorno apuntando al SDK. En PowerShell:
```powershell
$env:ANDROID_HOME = "C:\Users\<TU_USER>\AppData\Local\Android\Sdk"
```

### `gradlew assembleDebug` falla con "JAVA_HOME"

Configura JAVA_HOME apuntando a JDK 17:
```powershell
$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-17.x.x.x-hotspot"
```

### El APK abre y queda en blanco

- Abre Chrome → `chrome://inspect` y conecta el móvil con USB debugging.
- Mira los console errors del WebView.
- Causa típica: `sync-assets.js` no copió bien los paths. Re-ejecuta
  `npm run sync-assets` y reconstruye.

### El APK no puede conectar al PC

- ¿Mismo WiFi? El móvil y el PC tienen que estar en la misma red.
- ¿Firewall? Permite Ashley en Windows Defender Firewall (puerto 17300).
- ¿`allowMixedContent: true`? Sí, está configurado — el APK permite
  HTTP plano. Si lo cambias a `false`, el APK requerirá HTTPS.

### "App not installed" al instalar el APK

Causas comunes:
- Ya tienes una versión instalada con keystore diferente (debug vs
  release). Desinstala la anterior primero.
- Espacio insuficiente en el dispositivo.
- Versión Android < `minSdkVersion` (default Capacitor 6 es API 22 = Android 5.1).

## Versión del APK

El `versionCode` y `versionName` se gestionan en
`android/app/build.gradle`. Cuando bumpees la versión de Ashley desktop,
actualiza también:

```gradle
android {
    defaultConfig {
        versionCode 18002       // entero, monotónico (Play Store lo requiere)
        versionName "0.18.2"    // string, semver, visible al user
    }
}
```

(En CI considera autogenerar `versionCode` desde `${{ github.run_number }}`.)
