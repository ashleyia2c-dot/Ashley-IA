/**
 * cloudflared-tunnel.js — Gestión del túnel HTTPS para acceso móvil universal.
 *
 * v0.18.2 — Cloudflare Quick Tunnel integrado en Ashley desktop.
 *
 * Por qué: la conexión LAN PC↔móvil falla en muchos setups (boosters
 * con NAT, AP isolation, redes corporativas, distintas subnets, etc).
 * Ningún user va a configurar Tailscale o cambiar el modo de su router.
 *
 * Solución: Cloudflare Quick Tunnel (gratis, sin cuenta, sin rate limits).
 * Genera una URL pública HTTPS estable mientras el túnel está activo
 * (cambia entre arranques, no entre sesiones del mismo arranque).
 *
 * Flujo:
 *   1. Ashley arranca → backend Python en puerto local 17800
 *   2. Spawn cloudflared --url http://localhost:17800
 *   3. cloudflared imprime URL en stdout: https://abc-def.trycloudflare.com
 *   4. Captura URL + escribe a archivo (data dir) para que Python la lea
 *   5. Backend devuelve URL pública en /api/mobile/qr_payload
 *   6. QR contiene URL → móvil escanea desde CUALQUIER red (LAN, 4G, viaje)
 *   7. Móvil → Cloudflare → tu PC. Funciona.
 *
 * Auth: el backend ya tiene pairing token (CSPRNG 24 bytes). El túnel
 * es público pero requiere token para responder. Sin token = 401.
 *
 * Sin cuenta: estos son "Quick Tunnels" — efímeros, anónimos, gratis.
 * Cloudflare los ofrece para testing/dev pero permite uso comercial.
 */

'use strict';

const fs = require('fs');
const path = require('path');

// El paquete `cloudflared` maneja download del binario + spawn + capture URL.
let cloudflared = null;
try {
  cloudflared = require('cloudflared');
} catch (e) {
  // Disponibilidad opcional — si no está instalado, fallback a LAN simple
  console.warn('[tunnel] paquete cloudflared no disponible, modo LAN-only');
}

let _activeTunnel = null;          // { url, child, stop }
let _lastError = null;
let _statusListeners = [];          // callbacks(status, url, error)

const STATUS = {
  IDLE: 'idle',
  STARTING: 'starting',
  ACTIVE: 'active',
  FAILED: 'failed',
  STOPPED: 'stopped',
};
let _status = STATUS.IDLE;

function _setStatus(newStatus, url = null, error = null) {
  _status = newStatus;
  for (const cb of _statusListeners) {
    try { cb(newStatus, url, error); } catch {}
  }
}

/**
 * Subscribe a cambios de estado del túnel.
 * @param {Function} cb (status, url, error) => void
 */
function onStatusChange(cb) {
  _statusListeners.push(cb);
  // Push estado actual inmediatamente
  try { cb(_status, _activeTunnel?.url || null, _lastError); } catch {}
}

function getStatus() {
  return {
    status: _status,
    url: _activeTunnel?.url || null,
    error: _lastError,
  };
}

/**
 * Resuelve el path REAL al binario cloudflared, arreglando el bug clásico
 * de Electron + asar.
 *
 * v0.19.10 — root cause de "Error: spawn ...\app.asar\node_modules\cloudflared\bin\cloudflared.exe ENOENT":
 *
 * El paquete npm `cloudflared` calcula `bin` con `path.join(__dirname, 'bin', 'cloudflared.exe')`.
 * Cuando el módulo vive dentro de `app.asar`, __dirname devuelve un path tipo
 * `.../resources/app.asar/node_modules/cloudflared`. Aunque el config de
 * electron-builder tenga `asarUnpack: ['node_modules/cloudflared/**']` y el
 * binario REAL viva en `app.asar.unpacked/...`, el path que devuelve `bin`
 * sigue apuntando a la versión "virtual" dentro de asar — y `spawn()` NO
 * puede ejecutar binarios desde dentro de un asar archive.
 *
 * Fix: reemplazar manualmente `app.asar` → `app.asar.unpacked` en el path
 * antes de pasarlo a spawn. Si el archivo unpacked existe → usarlo. Si no
 * → fallback a download.
 */
function resolveCloudflaredBinPath(rawBin) {
  if (!rawBin) return rawBin;
  // Caso producción packaged: el path tiene `app.asar` pero el binario
  // real está en `app.asar.unpacked` (electron-builder asarUnpack).
  if (rawBin.includes(`${path.sep}app.asar${path.sep}`) ||
      rawBin.includes('/app.asar/')) {
    const unpacked = rawBin.replace(
      /([\\/])app\.asar([\\/])/,
      '$1app.asar.unpacked$2',
    );
    if (fs.existsSync(unpacked)) {
      return unpacked;
    }
    // Si el unpacked tampoco existe, devolvemos el rawBin para que el caller
    // ejecute la rama de download (cae a install()).
  }
  return rawBin;
}

/**
 * Verifica que cloudflared está disponible. Si no, intenta auto-instalar
 * el binario via el paquete npm (descarga al primer uso).
 *
 * v0.19.10 — añadido fallback robusto:
 *   1. Intenta path canonical de la npm package (con fix asar.unpacked)
 *   2. Si no existe físicamente → descarga via install() del paquete
 *   3. Si la descarga falla porque el package está dentro de asar → descarga
 *      a una ubicación alternativa en %APPDATA%\Ashley\bin\
 */
async function ensureCloudflaredBinary(log) {
  if (!cloudflared) {
    throw new Error('paquete cloudflared no instalado en node_modules');
  }
  const { bin: rawBin, install } = cloudflared;
  if (!rawBin) {
    throw new Error('cloudflared.bin no expuesto por el paquete');
  }

  // Fix asar — apunta al unpacked si estamos en build packagaged
  const bin = resolveCloudflaredBinPath(rawBin);
  if (fs.existsSync(bin)) {
    return bin;
  }

  // Si no existe en disco (ni el original ni el unpacked), intentamos
  // descargarlo. Primero al path original (puede fallar en asar — read-only).
  log(`Descargando cloudflared binary (~25MB) — solo primera vez...`);
  try {
    await install(bin);
    if (fs.existsSync(bin)) {
      log(`✓ cloudflared descargado a: ${bin}`);
      return bin;
    }
  } catch (e) {
    // EROFS / EACCES / asar virtual fs → usamos fallback
    log(`download al path canonical falló (${e.message}), probando fallback`);
  }

  // Fallback: descarga a %APPDATA%\Ashley\bin\cloudflared.exe (writable
  // siempre, sobrevive a re-installs del .exe principal).
  const userBinDir = path.join(
    process.env.APPDATA || process.env.HOME || '.',
    'Ashley',
    'bin',
  );
  try {
    fs.mkdirSync(userBinDir, { recursive: true });
  } catch {}
  const fallbackBin = path.join(userBinDir, 'cloudflared.exe');
  if (fs.existsSync(fallbackBin)) {
    log(`✓ cloudflared encontrado en fallback location: ${fallbackBin}`);
    return fallbackBin;
  }
  log(`Descargando cloudflared a fallback: ${fallbackBin}`);
  try {
    await install(fallbackBin);
    if (!fs.existsSync(fallbackBin)) {
      throw new Error('install() returned ok pero el archivo no se creó');
    }
    log(`✓ cloudflared descargado a fallback: ${fallbackBin}`);
    return fallbackBin;
  } catch (e) {
    throw new Error(`download de cloudflared falló (incluido fallback): ${e.message}`);
  }
}

/**
 * Arranca un Quick Tunnel apuntando al backend local.
 *
 * @param {object} opts
 * @param {number} opts.localPort — puerto del backend a exponer
 * @param {string} opts.tunnelUrlFile — path donde escribir la URL para Python
 * @param {Function} opts.log — logger (text → void)
 * @param {number} [opts.timeoutMs=30000] — timeout para captura de URL
 * @returns {Promise<{ok: boolean, url?: string, error?: string}>}
 */
async function startTunnel({ localPort, tunnelUrlFile, log, timeoutMs = 30000 } = {}) {
  if (!localPort) {
    return { ok: false, error: 'localPort required' };
  }
  if (_activeTunnel) {
    return { ok: true, url: _activeTunnel.url };
  }
  if (!cloudflared) {
    _setStatus(STATUS.FAILED, null, 'paquete cloudflared no disponible');
    return { ok: false, error: 'cloudflared not available' };
  }

  _setStatus(STATUS.STARTING);
  _lastError = null;

  try {
    await ensureCloudflaredBinary(log);

    log(`Arrancando Cloudflare Quick Tunnel → http://localhost:${localPort}`);
    const { tunnel } = cloudflared;
    const t = tunnel({ '--url': `http://localhost:${localPort}` });

    // `tunnel()` devuelve { url: Promise<string>, connections: ..., child, stop }
    _activeTunnel = {
      child: t.child,
      stop: t.stop,
      url: null,
    };

    // Race: capturar URL vs timeout
    const urlPromise = t.url;
    const timeoutPromise = new Promise((_, reject) =>
      setTimeout(() => reject(new Error(`timeout ${timeoutMs}ms esperando URL del túnel`)), timeoutMs)
    );

    const url = await Promise.race([urlPromise, timeoutPromise]);
    _activeTunnel.url = url;

    log(`✓ Túnel listo: ${url}`);

    // Persistir URL a disco para que el backend Python la lea
    if (tunnelUrlFile) {
      try {
        fs.mkdirSync(path.dirname(tunnelUrlFile), { recursive: true });
        fs.writeFileSync(tunnelUrlFile, url, 'utf-8');
      } catch (e) {
        log(`(warn) no pude escribir tunnel_url.txt: ${e.message}`);
      }
    }

    // Hook de exit: si cloudflared muere, limpiamos
    if (t.child) {
      t.child.on('exit', (code, signal) => {
        log(`cloudflared salió (code=${code}, signal=${signal})`);
        _activeTunnel = null;
        if (_status === STATUS.ACTIVE) {
          _setStatus(STATUS.STOPPED);
        }
        // Borrar URL del archivo (para que el backend sepa que el túnel cayó)
        if (tunnelUrlFile && fs.existsSync(tunnelUrlFile)) {
          try { fs.unlinkSync(tunnelUrlFile); } catch {}
        }
      });
    }

    _setStatus(STATUS.ACTIVE, url);
    return { ok: true, url };
  } catch (e) {
    const msg = (e && e.message) || String(e);
    log(`✗ Túnel falló: ${msg}`);
    _lastError = msg;
    _setStatus(STATUS.FAILED, null, msg);
    if (_activeTunnel?.stop) {
      try { _activeTunnel.stop(); } catch {}
    }
    _activeTunnel = null;
    return { ok: false, error: msg };
  }
}

/**
 * Para el túnel activo (si lo hay). Llamar en shutdown.
 */
function stopTunnel(log) {
  if (!_activeTunnel) return;
  try {
    if (_activeTunnel.stop) {
      _activeTunnel.stop();
    } else if (_activeTunnel.child) {
      _activeTunnel.child.kill();
    }
    if (log) log('Túnel detenido');
  } catch (e) {
    if (log) log(`Error parando túnel: ${e.message}`);
  }
  _activeTunnel = null;
  _setStatus(STATUS.STOPPED);
}

module.exports = {
  startTunnel,
  stopTunnel,
  onStatusChange,
  getStatus,
  STATUS,
};
