# Ashley Mobile Companion

App Android nativa (vía Capacitor) que se conecta a tu Ashley desktop.
**Pareo por QR** — un escaneo y listo.

## Para el COMPRADOR — flujo end-to-end

Si compraste Ashley, esto es lo que hay que hacer (~3 minutos total):

### 1️⃣ En tu PC (1 minuto)

1. Abre el correo de **Lemon Squeezy** que recibiste tras la compra.
2. Click en `ashley-desktop-X.Y.Z.exe` → descarga.
3. Doble click en el `.exe` → instalar.
4. Abre Ashley → introduce tu **license key** (también en el correo) → activar.

Ya tienes Ashley desktop corriendo. Su personalidad, voz, actions, todo activo.

### 2️⃣ En tu móvil Android (1 minuto)

1. Abre el **mismo correo** de Lemon Squeezy en tu móvil
   *(Gmail / Outlook / cualquier email app que tengas en el teléfono)*.
2. Click en `ashley-mobile-X.Y.Z.apk` → descarga.
3. Tap en el archivo descargado.
4. Android avisa de **"orígenes desconocidos"** — es esperable, da permiso.
5. Instalar → abrir.

### 3️⃣ Parear los dos (30 segundos)

1. En tu PC, en Ashley desktop, click en el botón **📱 Móvil** de la barra superior
   *(el icono de smartphone, junto a Settings)*.
2. Aparece un QR en el PC.
3. En tu móvil, en Ashley Mobile, tap **"Escanear QR"**.
4. Apunta al QR del PC → conectado.

🎉 Ya está. Empieza a chatear desde el móvil. Las conversaciones se sincronizan
con tu Ashley desktop.

### 4️⃣ Opcional — modo offline (otro minuto)

Si quieres que Ashley móvil siga funcionando cuando tu PC está apagado
(en el bus, en el café, viaje):

1. En la app móvil → Settings (⚙️ arriba a la derecha).
2. Sección **"Modo offline"**.
3. Selecciona proveedor (xAI o OpenRouter — el mismo que usas en el desktop).
4. Pega tu API key.
5. **Probar conexión** → ✓ OK.
6. **Guardar**.

Ahora Ashley móvil chatea sola incluso con el PC apagado. Las conversaciones
se sincronizan al PC cuando vuelves a casa y el móvil lo detecta.

---

## Setup tradicional (sin compra — modo dev)

Si estás desarrollando o probando localmente sin instalar el `.exe`:

### A. Abrir la página de pareo en tu PC

```
http://127.0.0.1:17300/mobile/connect.html
```

O ejecuta `python tools/mobile_setup.py` (abre el browser automático).

### B. Instalar la app móvil

Carga la PWA desde tu móvil (mismo WiFi):
```
http://<TU_IP>:17300/mobile/index.html
```

Chrome → menú `⋮` → **"Añadir a pantalla de inicio"** → aparece como app.

### C. Escanear el QR

1. Abre la app desde el móvil
2. Pulsa **"Escanear QR"**
3. Apunta al QR del PC
4. Conectado.

---

## Arquitectura técnica

```
PC — Ashley desktop                       Móvil — APK Capacitor (Android)
┌────────────────────────┐                ┌──────────────────────────┐
│ Wake word, voz, vision │                │ Chat (online + offline)  │
│ Actions del PC         │  ◄── HTTP ──►  │ Memoria local (IndexedDB)│
│ LLM client desktop     │  LAN/Tailscale │ Brain JS si offline      │
│ Memoria (source-of-    │                │ BYOK (xAI/OpenRouter)    │
│  truth)                │                │ QR scanner para pareo    │
│ Embedded server +      │                │                          │
│  pairing token auth    │                │                          │
└────────────────────────┘                └──────────────────────────┘
       │                                            │
       │       ┌─────────────────────────┐          │
       │       │   sync_state            │          │
       │       │   (memoria PC → móvil)  │  ◄───────┘
       └──────►│   sync_prompts          │
               │   (prompts cacheados)   │
               │   sync_push             │
               │   (mensajes offline →   │
               │    PC al volver online) │
               └─────────────────────────┘
```

**PC = source of truth.** El móvil cachea + sincroniza.
**Online**: el móvil delega al PC (Ashley completa).
**Offline**: el móvil corre brain JS local + LLM directo (Ashley lite).

## Acceso REMOTO (fuera de WiFi de casa)

**Tailscale** (gratis, recomendado):

1. Instala Tailscale en PC + móvil
2. En la app móvil → Settings → cambia el servidor a la IP Tailscale
   (ej: `http://100.x.x.x:17300` en lugar de la IP LAN)
3. Funciona desde cualquier red

Tailscale es VPN entre tus dispositivos. Más seguro que abrir puertos.

## Distribución como APK (sin Play Store)

Tres caminos para que tu hermana / amigos instalen Ashley sin Play Store.
De más fácil a más control:

### Opción A — PWABuilder.com (10 minutos, sin código)

Lo más rápido. Requiere PWA accesible vía HTTPS público (Tailscale Funnel
o Cloudflare Tunnel).

1. **HTTPS público** desde tu PC:
   ```bash
   tailscale funnel 17300
   # → https://tu-pc.tailnet-xxx.ts.net/
   ```
2. Abre <https://www.pwabuilder.com/>
3. Pega `https://tu-pc.tailnet-xxx.ts.net/mobile/`
4. Click "Package for stores" → Android → "Generate Package"
5. Descarga `.apk` (signed) o `.aab` (para Play Store)

**Pros:** zero setup, web GUI.
**Contras:** dependencias de servidor HTTPS, si Tailscale cae el APK no
abre. Requiere mantener el túnel siempre activo.

### Opción B — Capacitor + GitHub Actions (recomendado, offline-first)

El APK lleva la PWA bundleada (no depende de HTTPS público). Solo
necesita LAN o Tailscale para llegar al PC. Build automático por GH Actions.

```bash
# Local (desarrollo)
cd mobile-app
npm run init           # instala Capacitor + Android platform
npm run build:debug    # genera APK debug en android/app/build/outputs/apk/debug/
```

CI automático — push de tag `mobile-vX.Y.Z`:
```bash
git tag mobile-v0.18.2
git push origin mobile-v0.18.2
# → GitHub Action builda APK + crea Release con APK descargable
```

Distribución a tu hermana:
1. Descarga el `.apk` del Release de GitHub
2. Lo manda por Telegram / Drive / USB
3. En Android: Settings → Seguridad → "Permitir orígenes desconocidos"
4. Tap en el APK → instalar
5. Abre Ashley → escanea QR de tu PC → listo

**Pros:** offline-first, sin dependencia de HTTPS, build reproducible,
APK firmado con debug key (válido para sideload).
**Contras:** APK debug, no certificado de Play Protect (Android puede
mostrar warning al instalar). Para distribución masiva: pasar a release
keystore.

Detalles técnicos: ver `mobile-app/README.md` y
`.github/workflows/build-android-apk.yml`.

### Opción C — Bubblewrap (TWA, requiere Play Store)

Es lo que necesitas si quieres subir a Play Store eventualmente.
Requiere HTTPS público igual que PWABuilder.

```bash
npm install -g @bubblewrap/cli
bubblewrap init --manifest=https://tu-pc.tailnet-xxx.ts.net/mobile/manifest.json
bubblewrap build
# Output: app-release-signed.apk + app-release-bundle.aab
```

Subir a Play Store:

1. Cuenta Developer ($25 one-time): <https://play.google.com/console>
2. New app → carga el `.aab` (no el `.apk`)
3. Listing: nombre, descripción, screenshots
4. Privacy policy URL (requerido para apps de comunicación)
5. Submit for review (3-7 días)

Para Ashley v1: **Closed testing** primero (con tu hermana + amigos),
luego Production tras validar.

### Comparativa rápida

| Vía | Tiempo setup | HTTPS req. | Offline | Play Store | Recomendado para |
|-----|--------------|-----------|---------|------------|------------------|
| **PWABuilder** | 10 min | ✅ | ❌ | Opcional | Prototipo rápido |
| **Capacitor + GH Actions** | 30 min | ❌ | ✅ | No | Distribución directa, beta cerrada |
| **Bubblewrap** | 1-2 h | ✅ | ❌ | ✅ | Lanzamiento oficial |

## Troubleshooting

### El móvil dice "No se pudo conectar"

- ¿Mismo WiFi que el PC? Comprueba que ambos están en la misma red.
- ¿Firewall bloqueando? Windows puede bloquear conexiones entrantes
  al puerto 17300. Permite Ashley en Windows Defender Firewall.
- ¿Ashley desktop está abierta? Sin ella, no hay servidor.

### "QR no reconocido"

- ¿El QR es de Ashley? Solo escanea QRs generados por la página
  `connect.html`.
- ¿Token caducado? Si regeneraste el token desde el PC, los QRs
  antiguos ya no valen — abre la página de nuevo y escanea el QR
  actualizado.

### Cámara no funciona en el móvil

- Concede permiso de cámara cuando Chrome lo pida.
- Si no aparece el prompt: Chrome → Configuración → Sitios → Cámara
  → permite para la URL de tu PC.
- Como fallback, despliega "O introducir manualmente" y escribe
  servidor + token a mano (los ves en la página connect.html).

### Mensajes que mando desde móvil no aparecen en desktop

Conocido: el desktop Ashley carga el historial en memoria al arrancar.
Si mandas mensajes desde móvil mientras desktop está abierta, no los
ves en desktop hasta reiniciar. Sync real-time queda para v2.

### Quiero desactivar acceso LAN (modo paranoid)

Edita `%APPDATA%\Ashley\data\mobile_pairing.json` y añade:

```json
{
  "token": "...",
  "lan_disabled": true
}
```

Reinicia Ashley. El embedded server volverá a bind solo localhost.
La app móvil dejará de poder conectar (aún con token correcto).

## Limitaciones conocidas

- ❌ Sin notificaciones push (Web Push requiere HTTPS + complejidad)
- ❌ Sin voz móvil (TTS/STT son features desktop)
- ❌ Sin sync real-time desktop ↔ móvil
- ❌ PC debe estar encendido
- ❌ jsQR fallback no incluido — necesitas Chrome reciente con BarcodeDetector

Aceptables para v1. Iremos resolviendo según feedback real.

## Seguridad

El embedded server bind a `0.0.0.0` (LAN access) por defecto desde v0.18.2.
Razones:

- Reflex (el framework) ya bindea a 0.0.0.0 — la superficie de exposición
  ya estaba ahí
- La app móvil necesita LAN access para conectar
- Endpoints sensibles (`/api/mobile/*`) protegidos por pairing token (CSPRNG)
- Endpoint del token solo accesible desde localhost

Si te preocupa, modo paranoid disponible (ver troubleshooting arriba).
